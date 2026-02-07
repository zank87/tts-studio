import os
import time

import gradio as gr

from config import ALL_MODEL_NAMES, MODEL_VOICES, OUTPUT_DIR
from services.epub_parser import parse_file
from services.tts_engine import generate_speech
from services.audio_utils import merge_audio_files, create_zip


def create_audiobook_tab():
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
                        choices=ALL_MODEL_NAMES,
                        value=ALL_MODEL_NAMES[0],
                        label="Model",
                    )
                    voice_dropdown = gr.Dropdown(
                        choices=MODEL_VOICES[ALL_MODEL_NAMES[0]],
                        value=MODEL_VOICES[ALL_MODEL_NAMES[0]][0],
                        label="Voice",
                    )
                speed_slider = gr.Slider(
                    minimum=0.5, maximum=2.0, value=1.0, step=0.1,
                    label="Speed",
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
            voices = MODEL_VOICES.get(model_name, [])
            default = voices[0] if voices else None
            return gr.Dropdown(choices=voices, value=default)

        model_dropdown.change(
            fn=update_voices,
            inputs=[model_dropdown],
            outputs=[voice_dropdown],
        )

        # Generate audiobook
        def on_generate(
            selected_labels, chapters, model_name, voice, speed, progress=gr.Progress()
        ):
            if not selected_labels:
                gr.Warning("Please select at least one chapter.")
                return "", gr.File(visible=False)

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
                return "", gr.File(visible=False)

            timestamp = int(time.time())
            chapter_paths = []
            log_lines = []
            total = len(selected_chapters)

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
                        path = generate_speech(chunk, model_name, voice, speed)
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
                        chapter_paths.append(chapter_path)
                        log_lines.append(f"  Done: {title}")
                    else:
                        log_lines.append(f"  Skipped (empty): {title}")

                except Exception as e:
                    log_lines.append(f"  FAILED: {title} — {e}")
                    continue

            if not chapter_paths:
                log_lines.append("\nNo chapters were generated successfully.")
                return "\n".join(log_lines), gr.File(visible=False)

            # Create ZIP
            zip_path = os.path.join(OUTPUT_DIR, f"audiobook_{timestamp}.zip")
            create_zip(chapter_paths, zip_path)
            log_lines.append(f"\nDone! {len(chapter_paths)} chapters packaged into ZIP.")

            return "\n".join(log_lines), gr.File(value=zip_path, visible=True)

        generate_btn.click(
            fn=on_generate,
            inputs=[
                chapter_checkboxes, chapters_state,
                model_dropdown, voice_dropdown, speed_slider,
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
