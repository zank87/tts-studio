import gradio as gr

from config import DIALOGUE_MODEL_NAMES, TEXT_CHAR_LIMIT_WARNING
from services.audio_utils import maybe_convert_to_mp3
from services.model_manager import manager
from services.tts_engine import generate_dialogue

EXAMPLE_SCRIPT = """\
[S1] Hey, have you tried that new coffee place on Main Street?
[S2] (laughs) Oh yeah, I went there yesterday. The espresso is amazing.
[S1] Right? I think it might be the best in town.
[S2] (sighs) If only it weren't so far from the office."""


def create_dialogue_tab():
    with gr.Tab("Dialogue"):
        gr.Markdown("### Multi-Speaker Dialogue")
        gr.Markdown("Write a script with `[S1]` and `[S2]` speaker tags to generate a conversation.")
        status_text = gr.Textbox(label="Status", interactive=False, value="", visible=False)

        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Script",
                    value=EXAMPLE_SCRIPT,
                    lines=10,
                )
                model_dropdown = gr.Dropdown(
                    choices=DIALOGUE_MODEL_NAMES,
                    value=DIALOGUE_MODEL_NAMES[0],
                    label="Model",
                )
                with gr.Row():
                    format_radio = gr.Radio(
                        choices=["WAV", "MP3"], value="WAV", label="Output Format",
                    )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")
                gr.Markdown(
                    "**Tips:**\n"
                    "- Use `[S1]` and `[S2]` to indicate speakers\n"
                    "- Add nonverbals: `(laughs)`, `(sighs)`, `(clears throat)`, `(gasps)`\n"
                    "- Each line should start with a speaker tag"
                )

        def on_generate(text, model_name, output_format):
            if not text.strip():
                raise gr.Error("Please enter a script.")

            if len(text) > TEXT_CHAR_LIMIT_WARNING:
                gr.Warning(f"Text is {len(text):,} chars. Inputs over {TEXT_CHAR_LIMIT_WARNING:,} may be slow.")

            # Stage 1: Load model if needed
            if not manager.is_loaded(model_name):
                yield gr.update(value=f"Loading model {model_name}...", visible=True), gr.update()
                manager.get_model(model_name)

            # Stage 2: Generate audio
            yield gr.update(value="Generating audio...", visible=True), gr.update()

            try:
                path = generate_dialogue(text, model_name)
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
            inputs=[text_input, model_dropdown, format_radio],
            outputs=[status_text, audio_output],
        )
