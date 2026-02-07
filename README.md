# TTS Studio

A local text-to-speech web application powered by [MLX-Audio](https://github.com/Blaizzy/mlx-audio) on Apple Silicon. No cloud APIs, no GPU rentals — everything runs on your Mac.

## Features

- **Quick TTS** — Type text, pick a voice from 50+ presets, and generate speech instantly
- **Voice Cloning** — Upload a short audio clip of any voice and synthesize new speech in that voice
- **Audiobook Generator** — Upload an EPUB or TXT file, select chapters, and generate a downloadable ZIP of chapter audio files

## Hardware Requirements

- **Apple Silicon Mac** (M1/M2/M3/M4) — required for MLX
- **16GB RAM minimum** — one model loaded at a time
- **36GB RAM recommended** — comfortably run two models simultaneously with LRU caching

### Models

| Model | Size | Use |
|-------|------|-----|
| Kokoro-82M | ~200MB | Fast TTS with 54 preset voices across 9 languages |
| Qwen3-TTS Base | ~1.2GB | Higher quality speech + voice cloning |
| Qwen3-TTS CustomVoice | ~800MB | Voice cloning with emotion control |

Models download automatically from Hugging Face on first use and are cached locally.

## Setup

Requires Python 3.11 (mlx-audio has compatibility issues with 3.12+) and ffmpeg (used by mlx-audio to decode uploaded audio files for voice cloning).

```bash
# Install system dependencies
brew install python@3.11 ffmpeg

# Clone the repo and create a virtual environment
cd tts-app
python3.11 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Running

```bash
source .venv/bin/activate
python app.py
```

Open **http://localhost:7860** in your browser. The first generation will take longer as the model and voice data are downloaded and initialized.

## How It Works

1. **Model loading** — Models are lazy-loaded on first use and kept in an LRU cache (max 2 models in memory). Switching models evicts the least recently used one.
2. **Text-to-speech** — Text is converted to phonemes (via [misaki](https://github.com/hexgrad/misaki) for Kokoro), then the neural model generates a raw audio waveform.
3. **Voice cloning** — A reference audio clip is encoded into a speaker embedding. The model then generates new speech conditioned on that embedding.
4. **Audiobook generation** — EPUB/TXT files are parsed into chapters. Each chapter is split into ~2000 character chunks, generated sequentially to avoid memory issues, then merged into a single WAV per chapter and packaged as a ZIP.

All inference runs locally on your Mac's GPU and Neural Engine via Apple's [MLX](https://github.com/ml-explore/mlx) framework. No data leaves your machine.

## Tech Stack

- **[MLX-Audio](https://github.com/Blaizzy/mlx-audio)** — TTS inference engine optimized for Apple Silicon
- **[Gradio](https://www.gradio.app/)** — Web UI with native audio playback, file upload, and progress tracking
- **[misaki](https://github.com/hexgrad/misaki)** — Text-to-phoneme conversion for Kokoro
- **[ebooklib](https://github.com/aerkalov/ebooklib)** + **BeautifulSoup4** — EPUB parsing and HTML stripping
- **[soundfile](https://github.com/bastibe/python-soundfile)** — WAV audio I/O

## Project Structure

```
tts-app/
├── app.py                  # Gradio app entry point
├── config.py               # Model configs, voice lists, paths
├── requirements.txt
├── services/
│   ├── model_manager.py    # Lazy model loading with LRU cache
│   ├── tts_engine.py       # generate_speech() and clone_voice()
│   ├── epub_parser.py      # EPUB/TXT → chapter list
│   └── audio_utils.py      # WAV save, merge, ZIP packaging
└── ui/
    ├── quick_tts_tab.py    # Quick TTS tab
    ├── voice_clone_tab.py  # Voice Cloning tab
    └── audiobook_tab.py    # Audiobook Generator tab
```
