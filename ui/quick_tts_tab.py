import gradio as gr

from config import ALL_MODEL_NAMES, MODEL_VOICES
from services.tts_engine import generate_speech


def create_quick_tts_tab():
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
                        choices=MODEL_VOICES[ALL_MODEL_NAMES[0]],
                        value=MODEL_VOICES[ALL_MODEL_NAMES[0]][0],
                        label="Voice",
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
            voices = MODEL_VOICES.get(model_name, [])
            default = voices[0] if voices else None
            return gr.Dropdown(choices=voices, value=default)

        model_dropdown.change(
            fn=update_voices,
            inputs=[model_dropdown],
            outputs=[voice_dropdown],
        )

        # Generate speech
        def on_generate(text, model_name, voice, speed):
            if not text.strip():
                raise gr.Error("Please enter some text.")
            try:
                path = generate_speech(text, model_name, voice, speed)
                return path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Generation failed: {e}")

        generate_btn.click(
            fn=on_generate,
            inputs=[text_input, model_dropdown, voice_dropdown, speed_slider],
            outputs=[audio_output],
        )
