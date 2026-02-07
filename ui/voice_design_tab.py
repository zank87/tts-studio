import gradio as gr

from config import VOICE_DESIGN_MODEL_NAMES
from services.tts_engine import generate_voice_design


def create_voice_design_tab():
    with gr.Tab("Voice Design"):
        gr.Markdown("### Voice Design")
        gr.Markdown("Describe a voice in natural language and generate speech with it.")

        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Text to Speak",
                    placeholder="Enter text to speak...",
                    lines=5,
                )
                instruct_input = gr.Textbox(
                    label="Voice Description",
                    placeholder="A deep male voice with a calm tone and slow pace...",
                    lines=3,
                )
                with gr.Row():
                    language_dropdown = gr.Dropdown(
                        choices=["auto", "English", "Chinese"],
                        value="auto",
                        label="Language",
                    )
                    model_dropdown = gr.Dropdown(
                        choices=VOICE_DESIGN_MODEL_NAMES,
                        value=VOICE_DESIGN_MODEL_NAMES[0],
                        label="Model",
                    )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        def on_generate(text, instruct, language, model_name):
            if not text.strip():
                raise gr.Error("Please enter some text.")
            if not instruct.strip():
                raise gr.Error("Please describe the voice you want.")
            try:
                path = generate_voice_design(text, model_name, language, instruct)
                return path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Generation failed: {e}")

        generate_btn.click(
            fn=on_generate,
            inputs=[text_input, instruct_input, language_dropdown, model_dropdown],
            outputs=[audio_output],
        )
