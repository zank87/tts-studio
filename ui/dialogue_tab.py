import gradio as gr

from config import DIALOGUE_MODEL_NAMES
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
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")
                gr.Markdown(
                    "**Tips:**\n"
                    "- Use `[S1]` and `[S2]` to indicate speakers\n"
                    "- Add nonverbals: `(laughs)`, `(sighs)`, `(clears throat)`, `(gasps)`\n"
                    "- Each line should start with a speaker tag"
                )

        def on_generate(text, model_name):
            if not text.strip():
                raise gr.Error("Please enter a script.")
            try:
                path = generate_dialogue(text, model_name)
                return path
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Generation failed: {e}")

        generate_btn.click(
            fn=on_generate,
            inputs=[text_input, model_dropdown],
            outputs=[audio_output],
        )
