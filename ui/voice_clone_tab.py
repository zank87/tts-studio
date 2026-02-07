import gradio as gr

from config import CLONING_MODEL_NAMES, QWEN3_VOICE_LIST, TEXT_CHAR_LIMIT_WARNING, is_custom_voice_model
from services.audio_utils import maybe_convert_to_mp3
from services.model_manager import manager
from services.tts_engine import clone_voice
from services.voice_library import list_voices, get_voice, save_voice, delete_voice


def _voice_dropdown_choices():
    """Return list of (display_name, slug) tuples for saved voices."""
    return [(v["name"], v["slug"]) for v in list_voices()]


def create_voice_clone_tab():
    with gr.Tab("Voice Cloning"):
        gr.Markdown("### Clone a Voice")
        gr.Markdown(
            "Upload a reference audio clip (5-30 seconds recommended), "
            "optionally provide its transcript, and generate new speech in that voice."
        )
        status_text = gr.Textbox(label="Status", interactive=False, value="", visible=False)

        # ── Saved Voices row ──────────────────────────────────────────────
        gr.Markdown("#### Saved Voices")
        with gr.Row():
            saved_voice_dropdown = gr.Dropdown(
                choices=_voice_dropdown_choices(),
                value=None,
                label="Saved Voices",
                scale=3,
            )
            load_btn = gr.Button("Load", scale=1)
            delete_btn = gr.Button("Delete", variant="stop", scale=1)

        # ── Cloning controls ─────────────────────────────────────────────
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
                base_voice_dropdown = gr.Dropdown(
                    choices=QWEN3_VOICE_LIST,
                    value=QWEN3_VOICE_LIST[0],
                    label="Base Voice (CustomVoice only)",
                    visible=is_custom_voice_model(CLONING_MODEL_NAMES[0]),
                )
                instruct_input = gr.Textbox(
                    label="Style Instruction (CustomVoice only)",
                    placeholder="e.g. Speak with warmth and gentle encouragement",
                    lines=2,
                    visible=is_custom_voice_model(CLONING_MODEL_NAMES[0]),
                )
                text_input = gr.Textbox(
                    label="Text to Synthesize",
                    placeholder="Enter text for the cloned voice to speak...",
                    lines=5,
                )
                with gr.Row():
                    format_radio = gr.Radio(
                        choices=["WAV", "MP3"], value="WAV", label="Output Format",
                    )
                generate_btn = gr.Button("Generate", variant="primary")

            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")

        # ── Save Voice row ───────────────────────────────────────────────
        gr.Markdown("#### Save Current Voice")
        with gr.Row():
            save_name_input = gr.Textbox(
                label="Voice Name",
                placeholder="e.g. Dad - Calm",
                scale=3,
            )
            save_btn = gr.Button("Save Voice", variant="secondary", scale=1)

        # ── Handlers ─────────────────────────────────────────────────────

        def on_model_change(model_name):
            visible = is_custom_voice_model(model_name)
            return gr.Dropdown(visible=visible), gr.Textbox(visible=visible)

        model_dropdown.change(
            fn=on_model_change,
            inputs=[model_dropdown],
            outputs=[base_voice_dropdown, instruct_input],
        )

        def on_load(slug):
            if not slug:
                raise gr.Error("Please select a saved voice first.")
            try:
                voice = get_voice(slug)
            except FileNotFoundError:
                raise gr.Error("Saved voice not found. It may have been deleted.")
            model = voice.get("model", CLONING_MODEL_NAMES[0])
            base_voice = voice.get("base_voice", QWEN3_VOICE_LIST[0])
            show_base = is_custom_voice_model(model)
            return (
                voice["ref_audio_path"],
                voice.get("ref_text", ""),
                model,
                gr.Dropdown(value=base_voice, visible=show_base),
            )

        load_btn.click(
            fn=on_load,
            inputs=[saved_voice_dropdown],
            outputs=[ref_audio, ref_text, model_dropdown, base_voice_dropdown],
        )

        def on_delete(slug):
            if not slug:
                raise gr.Error("Please select a saved voice first.")
            try:
                delete_voice(slug)
            except FileNotFoundError:
                raise gr.Error("Voice not found. It may have already been deleted.")
            gr.Info("Voice deleted.")
            return gr.Dropdown(choices=_voice_dropdown_choices(), value=None)

        delete_btn.click(
            fn=on_delete,
            inputs=[saved_voice_dropdown],
            outputs=[saved_voice_dropdown],
        )

        def on_save(ref_audio_path, ref_text_val, model_name, base_voice, name):
            if not name or not name.strip():
                raise gr.Error("Please enter a voice name.")
            if not ref_audio_path:
                raise gr.Error("Please upload reference audio before saving.")
            try:
                save_voice(name, ref_audio_path, ref_text_val, model_name, base_voice)
            except ValueError as e:
                raise gr.Error(str(e))
            gr.Info(f"Voice '{name.strip()}' saved!")
            return gr.Dropdown(choices=_voice_dropdown_choices(), value=None)

        save_btn.click(
            fn=on_save,
            inputs=[ref_audio, ref_text, model_dropdown, base_voice_dropdown, save_name_input],
            outputs=[saved_voice_dropdown],
        )

        def on_generate(ref_audio_path, ref_text_val, model_name, base_voice, instruct, text, output_format):
            if not text.strip():
                raise gr.Error("Please enter text to synthesize.")
            if not ref_audio_path:
                raise gr.Error("Please upload reference audio.")

            if len(text) > TEXT_CHAR_LIMIT_WARNING:
                gr.Warning(f"Text is {len(text):,} chars. Inputs over {TEXT_CHAR_LIMIT_WARNING:,} may be slow.")

            # Stage 1: Load model if needed
            if not manager.is_loaded(model_name):
                yield gr.update(value=f"Loading model {model_name}...", visible=True), gr.update()
                manager.get_model(model_name)

            # Stage 2: Generate audio
            yield gr.update(value="Generating audio...", visible=True), gr.update()

            try:
                path = clone_voice(
                    text, model_name, ref_audio_path, ref_text_val,
                    voice=base_voice, instruct=instruct,
                )
            except gr.Error:
                raise
            except Exception as e:
                raise gr.Error(f"Voice cloning failed: {e}")

            # Stage 3: Convert format if needed
            if output_format == "MP3":
                yield gr.update(value="Converting to MP3...", visible=True), gr.update()
                path = maybe_convert_to_mp3(path, output_format)

            yield gr.update(value="", visible=False), path

        generate_btn.click(
            fn=on_generate,
            inputs=[ref_audio, ref_text, model_dropdown, base_voice_dropdown, instruct_input, text_input, format_radio],
            outputs=[status_text, audio_output],
        )
