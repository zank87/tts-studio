import gradio as gr

from services.audio_utils import check_ffmpeg
from ui.quick_tts_tab import create_quick_tts_tab
from ui.voice_clone_tab import create_voice_clone_tab
from ui.voice_design_tab import create_voice_design_tab
from ui.dialogue_tab import create_dialogue_tab
from ui.audiobook_tab import create_audiobook_tab
from ui.batch_compare_tab import create_batch_compare_tab


def main():
    with gr.Blocks(title="TTS Studio") as app:
        gr.Markdown("# TTS Studio")
        gr.Markdown("Local text-to-speech powered by MLX-Audio on Apple Silicon.")

        if not check_ffmpeg():
            gr.Markdown(
                "> **Warning:** `ffmpeg` was not found. "
                "MP3 export and non-WAV input conversion will not work. "
                "Install with `brew install ffmpeg`."
            )

        with gr.Tabs():
            create_quick_tts_tab()
            create_voice_clone_tab()
            create_voice_design_tab()
            create_dialogue_tab()
            create_audiobook_tab()
            create_batch_compare_tab()

    app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
