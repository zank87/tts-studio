import gradio as gr

from config import VOICE_DESIGN_MODEL_NAMES, TEXT_CHAR_LIMIT_WARNING
from services.audio_utils import maybe_convert_to_mp3
from services.model_manager import manager
from services.tts_engine import generate_voice_design


def create_voice_design_tab():
    with gr.Tab("Voice Design"):
        gr.Markdown("### Voice Design")
        gr.Markdown("Describe a voice in natural language and generate speech with it.")
        status_text = gr.Textbox(label="Status", interactive=False, value="", visible=False)

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
                with gr.Row():
                    format_radio = gr.Radio(
                        choices=["WAV", "MP3"], value="WAV", label="Output Format",
                    )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        def on_generate(text, instruct, language, model_name, output_format):
            if not text.strip():
                raise gr.Error("Please enter some text.")
            if not instruct.strip():
                raise gr.Error("Please describe the voice you want.")

            if len(text) > TEXT_CHAR_LIMIT_WARNING:
                gr.Warning(f"Text is {len(text):,} chars. Inputs over {TEXT_CHAR_LIMIT_WARNING:,} may be slow.")

            # Stage 1: Load model if needed
            if not manager.is_loaded(model_name):
                yield gr.update(value=f"Loading model {model_name}...", visible=True), gr.update()
                manager.get_model(model_name)

            # Stage 2: Generate audio
            yield gr.update(value="Generating audio...", visible=True), gr.update()

            try:
                path = generate_voice_design(text, model_name, language, instruct)
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Generation failed: {e}")

            # Stage 3: Convert format if needed
            if output_format == "MP3":
                yield gr.update(value="Converting to MP3...", visible=True), gr.update()
                path = maybe_convert_to_mp3(path, output_format)

            yield gr.update(value="", visible=False), path

        generate_btn.click(
            fn=on_generate,
            inputs=[text_input, instruct_input, language_dropdown, model_dropdown, format_radio],
            outputs=[status_text, audio_output],
        )
