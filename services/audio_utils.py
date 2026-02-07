import os
import zipfile

import numpy as np
import soundfile as sf

from config import DEFAULT_SAMPLE_RATE, OUTPUT_DIR


def save_audio(audio_array, path: str, sample_rate: int = DEFAULT_SAMPLE_RATE) -> str:
    """Save an mx.array or numpy array to a WAV file."""
    if not isinstance(audio_array, np.ndarray):
        audio_array = np.array(audio_array)
    # Ensure 1-D
    if audio_array.ndim > 1:
        audio_array = audio_array.flatten()
    sf.write(path, audio_array, sample_rate)
    return path


def merge_audio_files(
    paths: list[str],
    output_path: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    silence_ms: int = 250,
) -> str:
    """Concatenate WAV files with silence gaps between them."""
    silence_samples = int(sample_rate * silence_ms / 1000)
    silence = np.zeros(silence_samples, dtype=np.float32)

    segments = []
    for p in paths:
        data, sr = sf.read(p, dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        segments.append(data)
        segments.append(silence)

    if segments:
        segments.pop()  # remove trailing silence

    merged = np.concatenate(segments) if segments else np.zeros(1, dtype=np.float32)
    sf.write(output_path, merged, sample_rate)
    return output_path


def create_zip(audio_paths: list[str], output_path: str) -> str:
    """Pack multiple audio files into a ZIP."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in audio_paths:
            zf.write(p, os.path.basename(p))
    return output_path
