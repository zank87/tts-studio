import os
import time
import numpy as np

from config import (
    MODELS, DEFAULT_SAMPLE_RATE, OUTPUT_DIR,
    kokoro_lang_code, is_qwen3_model, is_custom_voice_model, get_sample_rate,
)
from services.model_manager import manager
from services.audio_utils import save_audio, ensure_wav


def generate_speech(
    text: str,
    model_name: str,
    voice: str,
    speed: float = 1.0,
) -> str:
    """Generate speech from text using a preset voice. Returns path to WAV file."""
    if not text.strip():
        raise ValueError("Text cannot be empty.")

    model = manager.get_model(model_name)
    timestamp = int(time.time() * 1000)
    output_path = os.path.join(OUTPUT_DIR, f"tts_{timestamp}.wav")

    audio_chunks = []

    if model_name == "Kokoro-82M":
        lang_code = kokoro_lang_code(voice)
        for result in model.generate(
            text=text,
            voice=voice,
            speed=speed,
            lang_code=lang_code,
        ):
            audio_chunks.append(np.array(result.audio))

    elif is_qwen3_model(model_name):
        language = _qwen3_language(voice)
        for result in model.generate(
            text=text,
            voice=voice,
            language=language,
        ):
            audio_chunks.append(np.array(result.audio))

    elif model_name == "CSM-1B":
        for result in model.generate(
            text=text,
            voice=voice,
            speaker=0,
        ):
            audio_chunks.append(np.array(result.audio))

    if not audio_chunks:
        raise RuntimeError("Model produced no audio output.")

    combined = np.concatenate(audio_chunks)
    save_audio(combined, output_path, sample_rate=get_sample_rate(model_name))
    return output_path


def clone_voice(
    text: str,
    model_name: str,
    ref_audio_path: str,
    ref_text: str = "",
    voice: str = "Chelsie",
) -> str:
    """Clone a voice from reference audio. Returns path to WAV file.

    The voice parameter is required for CustomVoice models (base speaker name).
    It is ignored for Base and CSM models.
    """
    if not text.strip():
        raise ValueError("Text cannot be empty.")
    if not ref_audio_path or not os.path.exists(ref_audio_path):
        raise ValueError("Reference audio file is required.")

    ref_audio_path = ensure_wav(ref_audio_path)
    model = manager.get_model(model_name)
    timestamp = int(time.time() * 1000)
    output_path = os.path.join(OUTPUT_DIR, f"clone_{timestamp}.wav")

    audio_chunks = []

    if is_qwen3_model(model_name):
        kwargs = {"text": text, "ref_audio": ref_audio_path}
        if ref_text.strip():
            kwargs["ref_text"] = ref_text.strip()
        if is_custom_voice_model(model_name):
            kwargs["voice"] = voice
        for result in model.generate(**kwargs):
            audio_chunks.append(np.array(result.audio))

    elif model_name == "CSM-1B":
        kwargs = {"text": text, "ref_audio": ref_audio_path, "speaker": 0}
        if ref_text.strip():
            kwargs["ref_text"] = ref_text.strip()
        for result in model.generate(**kwargs):
            audio_chunks.append(np.array(result.audio))

    else:
        raise ValueError(f"Model '{model_name}' does not support voice cloning.")

    if not audio_chunks:
        raise RuntimeError("Model produced no audio output.")

    combined = np.concatenate(audio_chunks)
    save_audio(combined, output_path, sample_rate=get_sample_rate(model_name))
    return output_path


def generate_voice_design(
    text: str,
    model_name: str,
    language: str,
    instruct: str,
) -> str:
    """Generate speech with a voice designed from a text description. Returns path to WAV file."""
    if not text.strip():
        raise ValueError("Text cannot be empty.")
    if not instruct.strip():
        raise ValueError("Voice description cannot be empty.")

    model = manager.get_model(model_name)
    timestamp = int(time.time() * 1000)
    output_path = os.path.join(OUTPUT_DIR, f"voicedesign_{timestamp}.wav")

    audio_chunks = []
    kwargs = {"text": text, "instruct": instruct}
    if language and language != "auto":
        kwargs["lang_code"] = language

    for result in model.generate(**kwargs):
        audio_chunks.append(np.array(result.audio))

    if not audio_chunks:
        raise RuntimeError("Model produced no audio output.")

    combined = np.concatenate(audio_chunks)
    save_audio(combined, output_path, sample_rate=get_sample_rate(model_name))
    return output_path


def generate_dialogue(
    text: str,
    model_name: str,
) -> str:
    """Generate multi-speaker dialogue audio. Returns path to WAV file."""
    if not text.strip():
        raise ValueError("Script cannot be empty.")

    model = manager.get_model(model_name)
    timestamp = int(time.time() * 1000)
    output_path = os.path.join(OUTPUT_DIR, f"dialogue_{timestamp}.wav")

    audio_chunks = []
    for result in model.generate(text=text):
        audio_chunks.append(np.array(result.audio))

    if not audio_chunks:
        raise RuntimeError("Model produced no audio output.")

    combined = np.concatenate(audio_chunks)
    save_audio(combined, output_path, sample_rate=get_sample_rate(model_name))
    return output_path


def _qwen3_language(voice: str) -> str:
    """Determine language from Qwen3 voice name."""
    chinese_voices = {"Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"}
    return "Chinese" if voice in chinese_voices else "English"
