import json
import os
import re
import shutil
from datetime import datetime, timezone

from config import VOICES_DIR


def _slugify(name: str) -> str:
    """Lowercase, strip non-word chars, collapse whitespace to hyphens."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def save_voice(
    name: str,
    ref_audio_path: str,
    ref_text: str,
    model_name: str,
    base_voice: str = "Chelsie",
) -> dict:
    """Save a voice profile to the library.

    Copies reference audio and writes a manifest file.
    Returns the saved manifest dict.
    Raises ValueError if name is empty or already exists.
    """
    if not name or not name.strip():
        raise ValueError("Voice name cannot be empty.")

    slug = _slugify(name)
    if not slug:
        raise ValueError("Voice name must contain at least one word character.")

    voice_dir = os.path.join(VOICES_DIR, slug)
    if os.path.exists(voice_dir):
        raise ValueError(f"A voice named '{name}' already exists.")

    os.makedirs(voice_dir)

    # Copy reference audio
    ref_dest = os.path.join(voice_dir, "reference.wav")
    shutil.copy2(ref_audio_path, ref_dest)

    # Write manifest
    manifest = {
        "name": name.strip(),
        "slug": slug,
        "ref_text": ref_text.strip() if ref_text else "",
        "model": model_name,
        "base_voice": base_voice,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = os.path.join(voice_dir, "voice.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def list_voices() -> list[dict]:
    """Return all saved voices sorted by name."""
    voices = []
    if not os.path.isdir(VOICES_DIR):
        return voices

    for entry in os.listdir(VOICES_DIR):
        manifest_path = os.path.join(VOICES_DIR, entry, "voice.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path) as f:
                voices.append(json.load(f))

    voices.sort(key=lambda v: v.get("name", "").lower())
    return voices


def get_voice(slug: str) -> dict:
    """Return a voice manifest with ref_audio_path added.

    Raises FileNotFoundError if the voice doesn't exist.
    """
    voice_dir = os.path.join(VOICES_DIR, slug)
    manifest_path = os.path.join(voice_dir, "voice.json")

    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"Voice '{slug}' not found.")

    with open(manifest_path) as f:
        manifest = json.load(f)

    manifest["ref_audio_path"] = os.path.join(voice_dir, "reference.wav")
    return manifest


def delete_voice(slug: str) -> None:
    """Delete a saved voice. Raises FileNotFoundError if missing."""
    voice_dir = os.path.join(VOICES_DIR, slug)
    if not os.path.isdir(voice_dir):
        raise FileNotFoundError(f"Voice '{slug}' not found.")

    shutil.rmtree(voice_dir)
