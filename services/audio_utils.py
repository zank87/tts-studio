import os
import shutil
import subprocess
import zipfile

import numpy as np
import soundfile as sf

from config import DEFAULT_SAMPLE_RATE, OUTPUT_DIR


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def convert_to_mp3(wav_path: str, mp3_path: str | None = None, bitrate: str = "192k") -> str:
    """Convert a WAV file to MP3 using ffmpeg. Returns the MP3 path."""
    if not check_ffmpeg():
        raise RuntimeError(
            "ffmpeg is not installed. Install with `brew install ffmpeg`."
        )
    if mp3_path is None:
        mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
    subprocess.run(
        ["ffmpeg", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", bitrate, "-y", mp3_path],
        capture_output=True,
        check=True,
    )
    return mp3_path


def maybe_convert_to_mp3(wav_path: str, output_format: str) -> str:
    """Convert to MP3 if requested, otherwise return wav_path unchanged."""
    if output_format == "MP3":
        return convert_to_mp3(wav_path)
    return wav_path


def ensure_wav(path: str) -> str:
    """Ensure an audio file is in WAV format miniaudio can decode.

    Returns the original path if it's already a valid WAV, otherwise
    converts it and returns the path to a new WAV file.
    """
    # Quick check: if it's already .wav and soundfile can read it, it's fine
    if path.lower().endswith(".wav"):
        try:
            sf.info(path)
            return path
        except Exception:
            pass

    wav_path = os.path.splitext(path)[0] + "_converted.wav"

    # Try soundfile first (handles FLAC, OGG/Vorbis, AIFF, etc.)
    try:
        data, sr = sf.read(path, dtype="float32")
        sf.write(wav_path, data, sr)
        return wav_path
    except Exception:
        pass

    # Fall back to ffmpeg (handles MP3, WebM, Opus, AAC, etc.)
    try:
        subprocess.run(
            ["ffmpeg", "-i", path, "-ar", "24000", "-ac", "1", "-y", wav_path],
            capture_output=True,
            check=True,
        )
        return wav_path
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ValueError(
            f"Could not convert audio file to WAV. "
            f"Please upload a WAV, MP3, or FLAC file. ({e})"
        )


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
