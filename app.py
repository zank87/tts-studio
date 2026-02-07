import gradio as gr

from ui.quick_tts_tab import create_quick_tts_tab
from ui.voice_clone_tab import create_voice_clone_tab
from ui.voice_design_tab import create_voice_design_tab
from ui.dialogue_tab import create_dialogue_tab
from ui.audiobook_tab import create_audiobook_tab


def main():
    with gr.Blocks(title="TTS Studio") as app:
        gr.Markdown("# TTS Studio")
        gr.Markdown("Local text-to-speech powered by MLX-Audio on Apple Silicon.")

        with gr.Tabs():
            create_quick_tts_tab()
            create_voice_clone_tab()
            create_voice_design_tab()
            create_dialogue_tab()
            create_audiobook_tab()

    app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
