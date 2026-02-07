import gradio as gr

from config import ALL_MODEL_NAMES, MODELS, MODEL_VOICES, QWEN3_VOICE_LIST, SAVED_VOICE_PREFIX
from services.tts_engine import generate_speech, clone_voice
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
    return model_name == "Qwen3-TTS-CustomVoice" and _is_saved_voice(voice)


def create_quick_tts_tab():
    initial_choices = _build_voice_choices(ALL_MODEL_NAMES[0])
    initial_voice = initial_choices[0] if initial_choices else None

    with gr.Tab("Quick TTS"):
        gr.Markdown("### Text to Speech")
        gr.Markdown("Type text and generate speech with a preset voice.")

        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Text",
                    placeholder="Enter text to speak...",
                    lines=5,
                )
                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        choices=ALL_MODEL_NAMES,
                        value=ALL_MODEL_NAMES[0],
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
                    visible=_should_show_base_voice(ALL_MODEL_NAMES[0], initial_voice),
                )
                speed_slider = gr.Slider(
                    minimum=0.5,
                    maximum=2.0,
                    value=1.0,
                    step=0.1,
                    label="Speed",
                )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        # Update voice choices when model changes
        def update_voices(model_name):
            voices = _build_voice_choices(model_name)
            default = voices[0] if voices else None
            return (
                gr.Dropdown(choices=voices, value=default),
                gr.Dropdown(visible=_should_show_base_voice(model_name, default)),
            )

        model_dropdown.change(
            fn=update_voices,
            inputs=[model_dropdown],
            outputs=[voice_dropdown, base_voice_dropdown],
        )

        # Show/hide base voice when voice selection changes
        def on_voice_change(model_name, voice):
            show = _should_show_base_voice(model_name, voice)
            # Default to the saved voice's stored base_voice when first shown
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

        # Generate speech
        def on_generate(text, model_name, voice, base_voice, speed):
            if not text.strip():
                raise gr.Error("Please enter some text.")

            # Check if this is a saved voice
            if _is_saved_voice(voice):
                voice_name = voice[len(SAVED_VOICE_PREFIX):]
                saved = list_voices()
                slug = None
                for v in saved:
                    if v["name"] == voice_name:
                        slug = v["slug"]
                        break
                if not slug:
                    raise gr.Error(f"Saved voice '{voice_name}' not found.")
                try:
                    voice_data = get_voice(slug)
                    path = clone_voice(
                        text,
                        voice_data.get("model", model_name),
                        voice_data["ref_audio_path"],
                        voice_data.get("ref_text", ""),
                        voice=base_voice,
                    )
                    return path
                except Exception as e:
                    raise gr.Error(f"Generation with saved voice failed: {e}")

            try:
                path = generate_speech(text, model_name, voice, speed)
                return path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Generation failed: {e}")

        generate_btn.click(
            fn=on_generate,
            inputs=[text_input, model_dropdown, voice_dropdown, base_voice_dropdown, speed_slider],
            outputs=[audio_output],
        )
