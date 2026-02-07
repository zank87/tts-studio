import gradio as gr

from config import CLONING_MODEL_NAMES
from services.tts_engine import clone_voice


def create_voice_clone_tab():
    with gr.Tab("Voice Cloning"):
        gr.Markdown("### Clone a Voice")
        gr.Markdown(
            "Upload a reference audio clip (5–30 seconds recommended), "
            "optionally provide its transcript, and generate new speech in that voice."
        )

        with gr.Row():
            with gr.Column(scale=2):
                ref_audio = gr.Audio(
                    label="Reference Audio",
                    type="filepath",
                )
                ref_text = gr.Textbox(
                    label="Reference Transcript (optional but recommended)",
                    placeholder="Type what is said in the reference audio...",
                    lines=2,
                )
                model_dropdown = gr.Dropdown(
                    choices=CLONING_MODEL_NAMES,
                    value=CLONING_MODEL_NAMES[0],
                    label="Model",
                )
                text_input = gr.Textbox(
                    label="Text to Synthesize",
                    placeholder="Enter text for the cloned voice to speak...",
                    lines=5,
                )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        def on_generate(ref_audio_path, ref_text_val, model_name, text):
            if not text.strip():
                raise gr.Error("Please enter text to synthesize.")
            if not ref_audio_path:
                raise gr.Error("Please upload reference audio.")
            try:
                path = clone_voice(text, model_name, ref_audio_path, ref_text_val)
                return path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Voice cloning failed: {e}")

        generate_btn.click(
            fn=on_generate,
            inputs=[ref_audio, ref_text, model_dropdown, text_input],
            outputs=[audio_output],
        )
