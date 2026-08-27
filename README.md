<div align="center">

# ⬡ Babel


[![CI](https://github.com/Ares19v/Babel/actions/workflows/ci.yml/badge.svg)](https://github.com/Ares19v/Babel/actions/workflows/ci.yml)

### Real-Time Multilingual Speech-to-English Translation Workstation

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/vite-8-646cff.svg)](https://vitejs.dev)
[![Whisper](https://img.shields.io/badge/whisper-large--v3-brightgreen.svg)](https://openai.com/research/whisper)
[![Groq](https://img.shields.io/badge/inference-Groq%20LPU-orange.svg)](https://groq.com)

Speak in **Hindi (or 99+ other languages)** into your microphone, play audio on your PC, or upload media files — **Babel** detects the spoken language and displays clean, accurate, real-time English subtitles right in front of you.

</div>

---

## 🌌 Key Features

- 🎙️ **Live Microphone Translation** — Speak naturally in Hindi, Hinglish, Spanish, French, Japanese, etc., and watch instant English subtitles stream onto your screen.
- ⚡ **Ultra-Fast Cloud Inference** — Powered by OpenAI's official `whisper-large-v3` on Groq LPUs for sub-500ms translation latency.
- 🧠 **Phrase-Aware VAD Gating** — Intelligent energy tracking & pause detection ($\ge 400\text{ms}$) sends complete coherent speech utterances, eliminating half-word hallucinations and transliteration artifacts.
- 🛡️ **Zero-Flicker & Clean English Output** — Automatic server-side Unicode filtering and anti-aliasing linear interpolation ensure high-contrast, pure English text.
- 📁 **Universal File Translation** — Drag & drop any audio or video file (`.mp3`, `.mp4`, `.mkv`, `.m4a`, `.wav`, `.webm`) for fast full-file English transcription with timestamps.
- 🖥️ **System Audio Capture** — Transcribe and translate any meeting, video, or livestream playing on your computer.
- ✨ **Aurora Borealis Glassmorphism UI** — Centered, distraction-free frosted glass console with animated Northern Lights plasma waves, active waveform indicators, live latency badges, one-click copy, and transcript export.

---

## 🏗️ Architecture

```
  [ Microphone / System Audio / File ]
                   │
                   ▼
  ┌────────────────────────────────────────────────────────┐
  │                   React 19 Frontend                    │
  │  - Web Audio Context (16kHz PCM stream)                │
  │  - Linear interpolation downsampler                    │
  │  - Aurora Borealis canvas & subtitle renderer          │
  └────────────────────────┬───────────────────────────────┘
                           │
                 WebSocket / REST API
                           │
                           ▼
  ┌────────────────────────────────────────────────────────┐
  │                 FastAPI Backend Server                 │
  │  - AudioRingBuffer: Energy Tracking & VAD Segmentation │
  │  - Silence & Noise Suppression Gating                  │
  │  - In-memory WAV assembly (zero-disk streaming)        │
  └────────────────────────┬───────────────────────────────┘
                           │
                Groq LPUs / Whisper API
                           │
                           ▼
  ┌────────────────────────────────────────────────────────┐
  │            Whisper Large-v3 Translation Engine         │
  │  - Multilingual Auto-Detection (99+ Languages)         │
  │  - Native task="translations" ➔ 100% English Output    │
  └────────────────────────────────────────────────────────┘
```

---

## 🌍 Supported Languages (➔ Translated to English)

Whisper Large-v3 supports **99 languages** with auto-detection. Speak any language and Babel outputs English:

| Category | Languages |
|---|---|
| **Tier 1 (High Accuracy)** | 🇮🇳 Hindi, 🇪🇸 Spanish, 🇫🇷 French, 🇩🇪 German, 🇯🇵 Japanese, 🇰🇷 Korean, 🇨🇳 Chinese (Mandarin), 🇮🇹 Italian, 🇵🇹 Portuguese, 🇷🇺 Russian, 🇸🇦 Arabic, 🇹🇷 Turkish, 🇳🇱 Dutch, 🇵🇱 Polish, 🇸🇪 Swedish |
| **Indic & Regional** | 🇮🇳 Hindi (हिन्दी), Hinglish, Urdu, Punjabi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam |
| **Global & European** | Vietnamese, Thai, Indonesian, Malay, Greek, Czech, Romanian, Hungarian, Finnish, Danish, Norwegian, Ukrainian, Hebrew |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **FFmpeg** (installed and available in PATH)
- **Groq API Key** (Free from [console.groq.com](https://console.groq.com))

### 2. Backend Setup
```powershell
cd server
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your Groq API key:
# GROQ_API_KEY=gsk_your_key_here
```

Start the backend:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```powershell
cd client
npm install
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)** in your browser, click **`Start Live Translation`**, and start speaking!

---

## 📡 API Reference

| Endpoint | Method | Protocol | Description |
|---|---|---|---|
| `/health` | `GET` | HTTP | Health check, active model, and backend status |
| `/ws/stream` | `GET` | WebSocket | Real-time binary PCM audio stream $\rightarrow$ live English subtitles |
| `/transcribe/file` | `POST` | HTTP | Multipart file upload $\rightarrow$ timestamped English transcript segments |
| `/docs` | `GET` | HTTP | Interactive Swagger API documentation |

### WebSocket Payload Specification

- **Client $\rightarrow$ Server:** Binary frames of `int16` PCM audio at 16,000 Hz (mono).
- **Server $\rightarrow$ Client:**
```json
{
  "type": "transcript",
  "text": "Tomorrow I am traveling to Delhi.",
  "language": "hi",
  "language_probability": 0.99,
  "words": [],
  "is_final": true,
  "latency_ms": 340
}
```

---

## 💻 Tech Stack

- **ASR & Translation:** OpenAI `whisper-large-v3` via Groq LPU API
- **VAD & Audio Segmentation:** Custom RMS Energy Tracking & Phrase Pause Buffer
- **Backend Framework:** FastAPI, Uvicorn, WebSockets, NumPy, FFmpeg-Python
- **Frontend Stack:** React 19, Vite, Zustand, Framer Motion, Lucide Icons, Canvas WebGL
- **Audio Capture:** HTML5 Web Audio API (`AudioContext`, `ScriptProcessorNode`, Linear Resampling)

---

## 📜 License

MIT License. Developed by Devansh Tyagi.

---

© 2025 Devansh Tyagi (Ares19v). All Rights Reserved.
