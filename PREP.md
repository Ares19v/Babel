# Study Prep Guide: Babel

Welcome! This guide is a beginner-friendly, step-by-step tutorial to help you understand and build real-time speech-to-text systems. You will learn about audio streaming over WebSockets, Voice Activity Detection (VAD), and serving modern Automatic Speech Recognition (ASR) models like **Whisper**.

---

## 🗺️ What We Are Building
Babel is a local-first **Real-Time Multilingual Speech Transcription & Translation** tool. It captures live audio from your microphone, streams it over WebSockets to a Python backend, and uses **faster-whisper** to generate English translations instantly.

### System Flow
```
[User Mic] ──(16kHz PCM Audio)──► [WebSocket] ──► [FastAPI Backend] ──► [Silero VAD (Speech Gate)] ──► [faster-whisper Engine] ──► [Local Agreement Algorithm (Flicker Filter)] ──► [React UI Subtitle Stream]
```

---

## 📚 Core Learning Prerequisites

Before writing code, make sure you understand:
1. **Audio Basics**:
   - **Sample Rate**: How many audio samples are captured per second (Whisper requires exactly **16,000 Hz / 16 kHz**).
   - **PCM Int16 Format**: Audio represented as a list of 16-bit integers.
2. **WebSockets**: A protocol that allows two-way, persistent, real-time communication (unlike standard HTTP where the client must request and wait for a response).
3. **Voice Activity Detection (VAD)**: A lightweight machine learning model that detects whether an audio segment contains active human speech or silence.

---

## 🛠️ Step-by-Step Implementation Guide

Let's build a mini-version of a WebSocket-based speech transcription pipeline!

### Step 1: Set Up the Environment
Create a folder and install the necessary libraries:
```bash
mkdir mini-babel
cd mini-babel
python -m venv venv
venv\Scripts\activate  # On Windows
pip install fastapi uvicorn websockets faster-whisper numpy
```

---

### Step 2: The Core ASR Inference Engine
Let's write a simple offline Python script `transcribe.py` to see how **faster-whisper** works:
```python
from faster_whisper import WhisperModel

# Load the smallest model for CPU/testing
model_size = "tiny"
print("Loading model...")
model = WhisperModel(model_size, device="cpu", compute_type="float32")

# Transcribe an audio file (replace 'audio.wav' with an actual 16kHz WAV file)
print("Transcribing...")
segments, info = model.transcribe("audio.wav", beam_size=5)

print(f"Detected language: {info.language} (Confidence: {info.language_probability:.2f})")
for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

---

### Step 3: Real-Time WebSocket Server
Now, let's create a real-time speech backend using FastAPI and WebSockets. Save this as `app.py`:
```python
import numpy as np
from fastapi import FastAPI, WebSocket
from faster_whisper import WhisperModel

app = FastAPI()

# Initialize faster-whisper model
print("Loading Model...")
model = WhisperModel("tiny", device="cpu", compute_type="float32")

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected!")
    
    audio_buffer = bytearray()
    
    try:
        while True:
            # 1. Receive binary PCM audio frames from the client
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
            
            # 2. Process in chunks of ~3 seconds of audio (16000 samples/sec * 2 bytes/sample * 3 = 96000 bytes)
            if len(audio_buffer) >= 96000:
                # Convert byte buffer to float32 NumPy array (Whisper expects floats between -1.0 and 1.0)
                pcm_data = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcribe the buffer
                segments, info = model.transcribe(pcm_data, beam_size=1)
                transcript = " ".join([seg.text for seg in segments])
                
                # 3. Send text back to client
                if transcript.strip():
                    await websocket.send_json({
                        "text": transcript,
                        "language": info.language
                    })
                
                # Keep the last 1 second for context overlap
                audio_buffer = audio_buffer[-32000:]
                
    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Start your backend:
```bash
python app.py
```

---

## 🔍 Key Deep Dive Topics

### 1. Local Agreement Algorithm (Flicker Reduction)
During real-time streaming, speech models generate "partial hypotheses". They might transcribe "I think" and then change their mind to "I thank". This causes subtitles on screen to flicker.
* **Solution**: The server stores previous partial sentences. Only when a word appears identically in *two consecutive* prediction windows does the system "commit" it to the screen.

### 2. Fine-Tuning ASR via PEFT / LoRA
To improve Whisper's performance on highly specific accents or low-resource languages (e.g. Hindi in Google FLEURS), we apply **Low-Rank Adaptation (LoRA)**. Instead of retraining all 1.5 billion parameters, we freeze the base model and train a tiny fraction of adapter weights, reducing VRAM usage and training time dramatically.

---

## 🎯 Verification Tasks

1. **Test the Pipeline**: Run the complete app locally using `Run_Project.bat` and watch real-time transcription on `http://localhost:5173`.
2. **Experiment with Models**: Try changing the `MODEL_SIZE` in `server/main.py` from `"large-v3-turbo"` to `"tiny"` or `"base"` and note the latency difference on your hardware.
