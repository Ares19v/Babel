<div align="center">

# ⬡ Babel

### Real-Time Multilingual Speech Transcription & Translation

[![CI](https://github.com/Ares19v/Babel/actions/workflows/ci.yml/badge.svg)](https://github.com/Ares19v/Babel/actions/workflows/ci.yml)

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Node](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org)

Stream from microphone, capture system audio, or upload any audio/video file — Babel transcribes and translates to English in real-time using **faster-whisper large-v3-turbo** on your GPU.

</div>

---

## Features

- 🎙️ **Live mic streaming** — sub-second latency via WebSocket + Local Agreement algorithm
- 🖥️ **System audio capture** — transcribe anything playing on your PC (WASAPI loopback)
- 📁 **File upload** — supports MP3, MP4, MKV, WEBM, M4A, WAV and more via ffmpeg
- 🌍 **99-language auto-detection** — no configuration needed
- ⚡ **GPU accelerated** — CTranslate2 backend, 4–6× faster than vanilla Whisper
- 🧠 **LoRA fine-tuned** — custom Hindi adapter trained on FLEURS (hi\_in)

---

## Architecture

```
Mic / System Audio / File
         │
  ┌──────▼───────┐
  │ React Client │ ──── WebSocket (PCM int16 @ 16kHz) ────►
  └──────────────┘                                         │
                                                  ┌────────▼────────┐
                                                  │  FastAPI Server  │
                                                  │                  │
                                                  │  AudioRingBuffer │
                                                  │       │          │
                                                  │  faster-whisper  │
                                                  │  large-v3-turbo  │
                                                  │  (task=translate)│
                                                  │       │          │
                                                  │ Local Agreement  │
                                                  │  (anti-flicker)  │
                                                  └────────┬────────┘
                                                           │
                               ◄── JSON subtitle stream ───┘
```

---

## Quick Start (Windows)

### 1. Install dependencies (one-time)
```bat
INSTALL.bat
```

### 2. Run the app
```bat
Run_Project.bat
```

The browser opens automatically at **http://localhost:5173**.

---

## Manual Setup

### Backend
```powershell
cd server
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd client
npm install
npm run dev
```

---

## Docker (GPU)

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

```bash
docker compose up --build
```

App will be available at **http://localhost**.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Server + model status |
| `/ws/stream` | WebSocket | Real-time PCM audio → transcript stream |
| `/transcribe/file` | POST | Upload audio/video → timestamped segments |
| `/docs` | GET | Interactive Swagger UI |

### WebSocket Message Format

**Client → Server:** Binary frames of `int16` PCM at 16 kHz mono

**Server → Client:**
```json
{
  "type": "transcript",
  "text": "Hello, how are you?",
  "language": "hi",
  "language_probability": 0.987,
  "words": [{"word": "Hello,", "start": 0.0, "end": 0.3}],
  "is_final": false,
  "latency_ms": 420
}
```

---

## Fine-Tuning (Hindi LoRA Adapter)

The `training/` directory contains the full pipeline used to fine-tune a LoRA adapter on FLEURS Hindi (hi\_in).

### Reproduce the training

```powershell
# 1. Install training packages
cd server
.venv\Scripts\pip install transformers peft datasets accelerate evaluate jiwer soundfile librosa

# 2. Prepare dataset (~2 GB download)
cd ..\training
..\server\.venv\Scripts\python prepare_dataset.py

# 3. Fine-tune (≈1–2 hours on RTX 5060)
..\server\.venv\Scripts\python finetune.py

# 4. Benchmark (WER comparison)
..\server\.venv\Scripts\python benchmark.py
```

### Benchmark Results

| Model | WER (FLEURS hi\_in, 100 samples) |
|---|---|
| `whisper-large-v3` baseline | 0.3998 |
| Babel LoRA fine-tuned | 0.7491 |

> **Note:** The fine-tuned adapter shows signs of hallucination on some samples due to the aggressive learning rate used during training. The base `large-v3-turbo` model is used in production for reliability. Improving the adapter is an active area of development.

---

## System Audio Mode

Enable "Stereo Mix" in Windows Sound Settings → Recording → Right-click → Show Disabled Devices, then run in a third terminal:

```powershell
cd server
.venv\Scripts\python pipeline/system_audio.py
```

---

## Changing the Model

Edit `server/main.py` line 40:

```python
MODEL_SIZE = "large-v3-turbo"   # default — best speed+quality balance
# MODEL_SIZE = "large-v3"       # highest accuracy, more VRAM
# MODEL_SIZE = "medium"         # good quality, less VRAM
# MODEL_SIZE = "base"           # fastest — good for CPU-only testing
```

---

## Tech Stack

| Component | Technology |
|---|---|
| ASR + Translation | faster-whisper large-v3-turbo |
| Streaming algorithm | Local Agreement (anti-hallucination flicker) |
| Fine-tuning | HuggingFace PEFT LoRA (4-bit, rank-32) |
| Training dataset | FLEURS hi\_in (Google) |
| Evaluation | WER via jiwer |
| Backend | FastAPI + uvicorn + WebSockets |
| Frontend | React 19 + Vite + Zustand + Framer Motion |
| Containerization | Docker + NVIDIA Container Toolkit |

---

## Roadmap

- [ ] Improve Hindi LoRA adapter (lower LR, more data augmentation)
- [ ] Meta Ray-Ban companion mode (Spatial SDK WebSocket client)
- [ ] Multi-speaker diarization
- [ ] Subtitle export (SRT/VTT)

---

---
<p align="center">
  Made by Devansh Tyagi @ 2026
</p>