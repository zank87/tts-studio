import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
VOICES_DIR = os.path.join(BASE_DIR, "voices")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)

SAVED_VOICE_PREFIX = "\U0001f3a4 "

DEFAULT_SAMPLE_RATE = 24000

# ── Model Definitions ──────────────────────────────────────────────────────────

MODELS = {
    "Kokoro-82M": {
        "repo_id": "mlx-community/Kokoro-82M-bf16",
        "supports_cloning": False,
        "description": "Fast TTS, 50+ preset voices (~200MB)",
    },
    "Qwen3-TTS-Base": {
        "repo_id": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16",
        "supports_cloning": True,
        "description": "Higher quality + voice cloning (~1.2GB)",
    },
    "Qwen3-TTS-CustomVoice": {
        "repo_id": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
        "supports_cloning": True,
        "description": "Cloning with emotion control (~800MB)",
    },
}

ALL_MODEL_NAMES = list(MODELS.keys())
CLONING_MODEL_NAMES = [k for k, v in MODELS.items() if v["supports_cloning"]]

# ── Kokoro Voices ──────────────────────────────────────────────────────────────

KOKORO_VOICES = {
    "American English - Female": [
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
        "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    ],
    "American English - Male": [
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
        "am_michael", "am_onyx", "am_puck", "am_santa",
    ],
    "British English - Female": [
        "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    ],
    "British English - Male": [
        "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    ],
    "Japanese - Female": [
        "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro",
    ],
    "Japanese - Male": [
        "jm_kumo",
    ],
    "Chinese - Female": [
        "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    ],
    "Chinese - Male": [
        "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
    ],
    "Spanish": ["ef_dora", "em_alex", "em_santa"],
    "French": ["ff_siwis"],
    "Hindi": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"],
    "Italian": ["if_sara", "im_nicola"],
    "Portuguese": ["pf_dora", "pm_alex", "pm_santa"],
}

# Flat list for dropdown
KOKORO_VOICE_LIST = []
for group, voices in KOKORO_VOICES.items():
    for v in voices:
        KOKORO_VOICE_LIST.append(v)

# ── Qwen3-TTS Voices ──────────────────────────────────────────────────────────

QWEN3_VOICES = {
    "English": ["Chelsie", "Ryan", "Aiden"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
}

QWEN3_VOICE_LIST = []
for group, voices in QWEN3_VOICES.items():
    for v in voices:
        QWEN3_VOICE_LIST.append(v)

# ── Voice map per model ────────────────────────────────────────────────────────

MODEL_VOICES = {
    "Kokoro-82M": KOKORO_VOICE_LIST,
    "Qwen3-TTS-Base": QWEN3_VOICE_LIST,
    "Qwen3-TTS-CustomVoice": QWEN3_VOICE_LIST,
}

# ── Kokoro language code lookup ────────────────────────────────────────────────

def kokoro_lang_code(voice: str) -> str:
    """Derive the lang_code from the voice prefix."""
    prefix_map = {
        "a": "a", "b": "b", "j": "j", "z": "z",
        "e": "e", "f": "f", "h": "h", "i": "i", "p": "p",
    }
    if voice and len(voice) >= 2:
        return prefix_map.get(voice[0], "a")
    return "a"
