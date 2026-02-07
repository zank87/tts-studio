import gradio as gr

from config import STANDARD_MODEL_NAMES, MODELS, MODEL_VOICES, SAVED_VOICE_PREFIX, TEXT_CHAR_LIMIT_WARNING
from services.audio_utils import maybe_convert_to_mp3
from services.model_manager import manager
from services.tts_engine import generate_speech, clone_voice
from services.voice_library import list_voices, get_voice

MAX_SLOTS = 4


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


def create_batch_compare_tab():
    with gr.Tab("Voice Comparison"):
        gr.Markdown("### Batch Voice Comparison")
        gr.Markdown("Generate the same text with multiple voices side-by-side.")
        status_text = gr.Textbox(label="Status", interactive=False, value="", visible=False)

        text_input = gr.Textbox(
            label="Text",
            placeholder="Enter text to compare across voices...",
            lines=5,
        )

        with gr.Row():
            num_voices = gr.Dropdown(
                choices=["2", "3", "4"],
                value="2",
                label="Number of Voices",
            )
            format_radio = gr.Radio(
                choices=["WAV", "MP3"], value="WAV", label="Output Format",
            )

        generate_btn = gr.Button("Generate All", variant="primary")

        # Build voice slot columns
        model_dropdowns = []
        voice_dropdowns = []
        audio_outputs = []
        slot_columns = []

        initial_choices = _build_voice_choices(STANDARD_MODEL_NAMES[0])
        initial_voice = initial_choices[0] if initial_choices else None

        with gr.Row():
            for i in range(MAX_SLOTS):
                visible = i < 2  # show first 2 by default
                with gr.Column(visible=visible) as col:
                    md = gr.Dropdown(
                        choices=STANDARD_MODEL_NAMES,
                        value=STANDARD_MODEL_NAMES[0],
                        label=f"Voice {i+1} — Model",
                    )
                    vd = gr.Dropdown(
                        choices=initial_choices,
                        value=initial_voice,
                        label=f"Voice {i+1} — Voice",
                    )
                    ao = gr.Audio(label=f"Voice {i+1} Output", type="filepath")
                    model_dropdowns.append(md)
                    voice_dropdowns.append(vd)
                    audio_outputs.append(ao)
                    slot_columns.append(col)

        # Show/hide columns when num_voices changes
        def on_num_voices_change(n):
            n = int(n)
            return [gr.Column(visible=(i < n)) for i in range(MAX_SLOTS)]

        num_voices.change(
            fn=on_num_voices_change,
            inputs=[num_voices],
            outputs=slot_columns,
        )

        # Wire model → voice dropdown updates using a factory to capture index
        def _make_model_change_handler(idx):
            def handler(model_name):
                voices = _build_voice_choices(model_name)
                default = voices[0] if voices else None
                return gr.Dropdown(choices=voices, value=default)
            return handler

        for i in range(MAX_SLOTS):
            model_dropdowns[i].change(
                fn=_make_model_change_handler(i),
                inputs=[model_dropdowns[i]],
                outputs=[voice_dropdowns[i]],
            )

        # Generate all voices sequentially, yielding intermediate progress
        def on_generate(text, n_voices, output_format, *slot_args):
            if not text.strip():
                raise gr.Error("Please enter some text.")

            if len(text) > TEXT_CHAR_LIMIT_WARNING:
                gr.Warning(f"Text is {len(text):,} chars. Inputs over {TEXT_CHAR_LIMIT_WARNING:,} may be slow.")

            n = int(n_voices)
            # slot_args = model_0, voice_0, model_1, voice_1, ...
            models = [slot_args[i * 2] for i in range(MAX_SLOTS)]
            voices = [slot_args[i * 2 + 1] for i in range(MAX_SLOTS)]

            results = [None] * MAX_SLOTS

            def _audio_updates():
                return [
                    gr.update(value=results[j]) if results[j] else gr.update()
                    for j in range(MAX_SLOTS)
                ]

            for i in range(n):
                model_name = models[i]
                voice = voices[i]

                # Determine effective model for saved voices
                effective_model = model_name
                voice_data = None
                if _is_saved_voice(voice):
                    voice_name = voice[len(SAVED_VOICE_PREFIX):]
                    slug = None
                    for v in list_voices():
                        if v["name"] == voice_name:
                            slug = v["slug"]
                            break
                    if not slug:
                        gr.Warning(f"Voice {i+1}: saved voice '{voice_name}' not found.")
                        continue
                    voice_data = get_voice(slug)
                    effective_model = voice_data.get("model", model_name)

                # Stage: Load model if needed
                if not manager.is_loaded(effective_model):
                    yield [gr.update(value=f"Voice {i+1}/{n}: Loading model {effective_model}...", visible=True)] + _audio_updates()
                    manager.get_model(effective_model)

                # Stage: Generate
                yield [gr.update(value=f"Voice {i+1}/{n}: Generating audio...", visible=True)] + _audio_updates()

                try:
                    if voice_data:
                        path = clone_voice(
                            text,
                            effective_model,
                            voice_data["ref_audio_path"],
                            voice_data.get("ref_text", ""),
                        )
                    else:
                        path = generate_speech(text, model_name, voice, speed=1.0)

                    # Stage: Convert if needed
                    if output_format == "MP3":
                        yield [gr.update(value=f"Voice {i+1}/{n}: Converting to MP3...", visible=True)] + _audio_updates()
                        path = maybe_convert_to_mp3(path, output_format)

                    results[i] = path
                except Exception as e:
                    gr.Warning(f"Voice {i+1} failed: {e}")

            # Final yield: hide status, return all audio
            yield [gr.update(value="", visible=False)] + [
                gr.update(value=results[j]) for j in range(MAX_SLOTS)
            ]

        # Build inputs list: text, num_voices, format, then model/voice pairs
        gen_inputs = [text_input, num_voices, format_radio]
        for i in range(MAX_SLOTS):
            gen_inputs.append(model_dropdowns[i])
            gen_inputs.append(voice_dropdowns[i])

        gen_outputs = [status_text] + audio_outputs

        generate_btn.click(
            fn=on_generate,
            inputs=gen_inputs,
            outputs=gen_outputs,
        )
