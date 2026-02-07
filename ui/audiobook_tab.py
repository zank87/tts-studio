import os
import time

import gradio as gr

from config import STANDARD_MODEL_NAMES, MODELS, MODEL_VOICES, OUTPUT_DIR, QWEN3_VOICE_LIST, SAVED_VOICE_PREFIX, TEXT_CHAR_LIMIT_WARNING, is_custom_voice_model
from services.epub_parser import parse_file
from services.model_manager import manager
from services.tts_engine import generate_speech, clone_voice
from services.audio_utils import merge_audio_files, create_zip, maybe_convert_to_mp3
from services.voice_library import list_voices, get_voice


def _build_voice_choices(model_name: str) -> list[str]:
    """Return voice choices for a model, prepending saved voices if it supports cloning."""
    preset_voices = MODEL_VOICES.get(model_name, [])
    if not MODELS.get(model_name, {}).get("supports_cloning"):
        return preset_voices

    saved = list_voices()
    saved_choices = [SAVED_VOICE_PREFIX + v["name"] for v in saved]
    return saved_choices + preset_voices


def _is_saved_voice(voice: str) -> bool:
    return bool(voice and voice.startswith(SAVED_VOICE_PREFIX))


def _should_show_base_voice(model_name: str, voice: str) -> bool:
    return is_custom_voice_model(model_name) and _is_saved_voice(voice)


def create_audiobook_tab():
    initial_choices = _build_voice_choices(STANDARD_MODEL_NAMES[0])
    initial_voice = initial_choices[0] if initial_choices else None

    with gr.Tab("Audiobook"):
        gr.Markdown("### Audiobook Generator")
        gr.Markdown("Upload an EPUB or TXT file, select chapters, and generate audio for each.")

        with gr.Row():
            with gr.Column(scale=2):
                file_upload = gr.File(
                    label="Upload Book (.epub or .txt)",
                    file_types=[".epub", ".txt"],
                )
                chapter_checkboxes = gr.CheckboxGroup(
                    choices=[],
                    label="Chapters",
                    visible=False,
                )
                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        choices=STANDARD_MODEL_NAMES,
                        value=STANDARD_MODEL_NAMES[0],
                        label="Model",
                    )
                    voice_dropdown = gr.Dropdown(
                        choices=initial_choices,
                        value=initial_voice,
                        label="Voice",
                    )
                base_voice_dropdown = gr.Dropdown(
                    choices=QWEN3_VOICE_LIST,
                    value=QWEN3_VOICE_LIST[0],
                    label="Base Voice (CustomVoice only)",
                    visible=_should_show_base_voice(STANDARD_MODEL_NAMES[0], initial_voice),
                )
                instruct_input = gr.Textbox(
                    label="Style Instruction (CustomVoice only)",
                    placeholder="e.g. Calm, slow, bedtime story tone",
                    lines=2,
                    visible=is_custom_voice_model(STANDARD_MODEL_NAMES[0]),
                )
                speed_slider = gr.Slider(
                    minimum=0.5, maximum=2.0, value=1.0, step=0.1,
                    label="Speed",
                )
                with gr.Row():
                    format_radio = gr.Radio(
                        choices=["WAV", "MP3"], value="WAV", label="Output Format",
                    )
                generate_btn = gr.Button("Generate Audiobook", variant="primary")

            with gr.Column(scale=1):
                status_log = gr.Textbox(
                    label="Status",
                    lines=10,
                    interactive=False,
                )
                zip_output = gr.File(label="Download ZIP", visible=False)

        # State to hold parsed chapters
        chapters_state = gr.State([])

        # Parse uploaded file
        def on_file_upload(file):
            if file is None:
                return gr.CheckboxGroup(choices=[], visible=False), []
            try:
                chapters = parse_file(file.name)
                if not chapters:
                    gr.Warning("No chapters found in file.")
                    return gr.CheckboxGroup(choices=[], visible=False), []
                labels = [f"{ch['order']}: {ch['title']}" for ch in chapters]
                return (
                    gr.CheckboxGroup(choices=labels, value=labels, visible=True),
                    chapters,
                )
            except Exception as e:
                gr.Error(f"Failed to parse file: {e}")
                return gr.CheckboxGroup(choices=[], visible=False), []

        file_upload.change(
            fn=on_file_upload,
            inputs=[file_upload],
            outputs=[chapter_checkboxes, chapters_state],
        )

        # Update voice choices when model changes
        def update_voices(model_name):
            voices = _build_voice_choices(model_name)
            default = voices[0] if voices else None
            return (
                gr.Dropdown(choices=voices, value=default),
                gr.Dropdown(visible=_should_show_base_voice(model_name, default)),
                gr.Textbox(visible=is_custom_voice_model(model_name)),
            )

        model_dropdown.change(
            fn=update_voices,
            inputs=[model_dropdown],
            outputs=[voice_dropdown, base_voice_dropdown, instruct_input],
        )

        # Show/hide base voice when voice selection changes
        def on_voice_change(model_name, voice):
            show = _should_show_base_voice(model_name, voice)
            if show and _is_saved_voice(voice):
                voice_name = voice[len(SAVED_VOICE_PREFIX):]
                for v in list_voices():
                    if v["name"] == voice_name:
                        data = get_voice(v["slug"])
                        stored = data.get("base_voice", QWEN3_VOICE_LIST[0])
                        return gr.Dropdown(visible=True, value=stored)
            return gr.Dropdown(visible=show)

        voice_dropdown.change(
            fn=on_voice_change,
            inputs=[model_dropdown, voice_dropdown],
            outputs=[base_voice_dropdown],
        )

        # Resolve saved voice data if selected
        def _resolve_voice(voice, model_name):
            """Return (is_saved, voice_data_or_None)."""
            if _is_saved_voice(voice):
                voice_name = voice[len(SAVED_VOICE_PREFIX):]
                saved = list_voices()
                for v in saved:
                    if v["name"] == voice_name:
                        return True, get_voice(v["slug"])
                raise ValueError(f"Saved voice '{voice_name}' not found.")
            return False, None

        # Generate audiobook
        def on_generate(
            selected_labels, chapters, model_name, voice, base_voice, instruct, speed, output_format,
            progress=gr.Progress(),
        ):
            if not selected_labels:
                gr.Warning("Please select at least one chapter.")
                yield "", gr.File(visible=False)
                return

            # Resolve voice once before the loop
            try:
                is_saved, voice_data = _resolve_voice(voice, model_name)
            except ValueError as e:
                raise gr.Error(str(e))

            # Map selected labels back to chapter dicts
            selected_orders = set()
            for label in selected_labels:
                order_str = label.split(":")[0].strip()
                try:
                    selected_orders.add(int(order_str))
                except ValueError:
                    pass

            selected_chapters = [ch for ch in chapters if ch["order"] in selected_orders]
            if not selected_chapters:
                gr.Warning("No valid chapters selected.")
                yield "", gr.File(visible=False)
                return

            # Warn about total content length
            total_chars = sum(len(ch["content"]) for ch in selected_chapters)
            if total_chars > TEXT_CHAR_LIMIT_WARNING:
                gr.Warning(f"Total text is {total_chars:,} chars. Inputs over {TEXT_CHAR_LIMIT_WARNING:,} may be slow.")

            # Pre-load model if needed
            effective_model = model_name
            if is_saved and voice_data:
                effective_model = voice_data.get("model", model_name)
            if not manager.is_loaded(effective_model):
                yield f"Loading model {effective_model}...", gr.File(visible=False)
                manager.get_model(effective_model)

            timestamp = int(time.time())
            chapter_paths = []
            log_lines = []
            total = len(selected_chapters)
            ext = "mp3" if output_format == "MP3" else "wav"

            for i, ch in enumerate(progress.tqdm(selected_chapters, desc="Generating chapters")):
                title = ch["title"]
                log_lines.append(f"[{i+1}/{total}] Generating: {title}")

                try:
                    # Split long chapters into chunks
                    content = ch["content"]
                    chunks = _split_text(content, max_chars=2000)
                    chunk_paths = []

                    for ci, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue
                        if is_saved:
                            path = clone_voice(
                                chunk,
                                voice_data.get("model", model_name),
                                voice_data["ref_audio_path"],
                                voice_data.get("ref_text", ""),
                                voice=base_voice,
                                instruct=instruct,
                            )
                        else:
                            path = generate_speech(chunk, model_name, voice, speed, instruct=instruct)
                        chunk_paths.append(path)

                    if chunk_paths:
                        chapter_path = os.path.join(
                            OUTPUT_DIR, f"audiobook_{timestamp}_ch{ch['order']:03d}.wav"
                        )
                        if len(chunk_paths) == 1:
                            os.rename(chunk_paths[0], chapter_path)
                        else:
                            merge_audio_files(chunk_paths, chapter_path)
                            # Clean up chunk files
                            for cp in chunk_paths:
                                if os.path.exists(cp):
                                    os.remove(cp)
                        chapter_path = maybe_convert_to_mp3(chapter_path, output_format)
                        chapter_paths.append(chapter_path)
                        log_lines.append(f"  Done: {title}")
                    else:
                        log_lines.append(f"  Skipped (empty): {title}")

                except Exception as e:
                    log_lines.append(f"  FAILED: {title} — {e}")
                    continue

            if not chapter_paths:
                log_lines.append("\nNo chapters were generated successfully.")
                yield "\n".join(log_lines), gr.File(visible=False)
                return

            # Create ZIP
            zip_path = os.path.join(OUTPUT_DIR, f"audiobook_{timestamp}.zip")
            create_zip(chapter_paths, zip_path)
            log_lines.append(f"\nDone! {len(chapter_paths)} chapters packaged into ZIP.")

            yield "\n".join(log_lines), gr.File(value=zip_path, visible=True)

        generate_btn.click(
            fn=on_generate,
            inputs=[
                chapter_checkboxes, chapters_state,
                model_dropdown, voice_dropdown, base_voice_dropdown, instruct_input, speed_slider, format_radio,
            ],
            outputs=[status_log, zip_output],
        )


def _split_text(text: str, max_chars: int = 2000) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) > max_chars and current:
            chunks.append(current.strip())
            current = ""
        current += s + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]
