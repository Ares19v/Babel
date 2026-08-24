"""
Babel FastAPI Server — main entry point.

Endpoints:
  GET  /health            — liveness probe
  WS   /ws/stream         — real-time mic/system audio streaming
  POST /transcribe/file   — upload an audio/video file for translation

Design notes:
  - Single global WhisperModel instance (thread-safe via internal lock)
  - WebSocket audio: binary frames of int16 PCM at 16kHz mono
  - File uploads: ffmpeg extracts 16kHz mono WAV then full-file inference
  - CORS open for local React dev (restrict in production)
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import ffmpeg
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pipeline.audio_buffer import AudioRingBuffer
from pipeline.transcriber import StreamingTranscriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("babel.server")

# ── Configuration (override via .env) ────────────────────────────────────────
MODEL_SIZE   = os.getenv("BABEL_MODEL_SIZE", "large-v3-turbo")
DEVICE       = os.getenv("BABEL_DEVICE", "cuda")
COMPUTE_TYPE = os.getenv("BABEL_COMPUTE_TYPE", "float16")
SAMPLE_RATE  = 16_000
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "BABEL_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]


# ── App lifecycle ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"⚡ Initializing Groq Whisper API (whisper-large-v3-turbo)...")
    app.state.transcriber = StreamingTranscriber(
        model_size=MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
    )
    logger.info("✅ Babel server ready — using Groq Whisper for English translation")
    yield
    logger.info("👋 Shutting down")


app = FastAPI(title="Babel", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "whisper-large-v3-turbo",
        "backend": "groq-api",
        "task": "translations → English",
    }


# ── WebSocket streaming endpoint ───────────────────────────────────────────────
@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    await ws.accept()
    transcriber: StreamingTranscriber = ws.app.state.transcriber
    buffer = AudioRingBuffer(max_seconds=30, sample_rate=SAMPLE_RATE)
    loop = asyncio.get_event_loop()

    logger.info(f"Client connected: {ws.client}")

    # Announce readiness
    await ws.send_json({
        "type": "status",
        "status": "ready",
        "model": MODEL_SIZE,
        "device": DEVICE,
    })

    try:
        while True:
            msg = await ws.receive()

            # ── Binary audio frames (int16 PCM, 16kHz mono) ──────────────
            if "bytes" in msg and msg["bytes"]:
                raw = msg["bytes"]
                audio_i16 = np.frombuffer(raw, dtype=np.int16)
                audio_f32 = audio_i16.astype(np.float32) / 32768.0
                buffer.push(audio_f32)

                if buffer.ready_to_process():
                    window = buffer.get_window()
                    t0 = time.perf_counter()
                    result = await loop.run_in_executor(
                        None, transcriber.process_window, window
                    )
                    if result:
                        result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
                        await ws.send_json(result)

            # ── JSON control messages ─────────────────────────────────────
            elif "text" in msg and msg["text"]:
                try:
                    data = json.loads(msg["text"])
                    mtype = data.get("type", "")

                    if mtype == "ping":
                        await ws.send_json({"type": "pong", "ts": time.time()})

                    elif mtype == "reset":
                        buffer.reset()
                        transcriber.reset()
                        await ws.send_json({"type": "status", "status": "ready"})
                        logger.info("Session reset")

                    elif mtype == "set_language":
                        lang = data.get("language")
                        transcriber.set_forced_language(lang)
                        await ws.send_json({"type": "status", "status": "language_updated", "language": lang})
                        logger.info(f"Language updated to: {lang}")

                    elif mtype == "set_model":
                        # Future: hot-swap model size
                        pass

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {ws.client}")
    except RuntimeError as exc:
        if "Cannot call" in str(exc) and "disconnect" in str(exc):
            logger.info(f"Client disconnected abruptly: {ws.client}")
        else:
            logger.error(f"WS Runtime error: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"WS error: {exc}", exc_info=True)
        try:
            await ws.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


# ── File upload endpoint ───────────────────────────────────────────────────────
@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    """
    Accept any audio/video file, extract 16kHz mono audio via ffmpeg,
    run full Whisper translate inference, return timestamped segments.
    """
    transcriber: StreamingTranscriber = app.state.transcriber

    suffix = Path(file.filename or "upload").suffix or ".tmp"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    wav_path = tmp_path.with_suffix(".babel.wav")

    try:
        # Extract audio — ffmpeg handles MP3, MP4, MKV, WEBM, M4A, etc.
        (
            ffmpeg
            .input(str(tmp_path))
            .output(
                str(wav_path),
                ar=SAMPLE_RATE,
                ac=1,
                format="wav",
                acodec="pcm_s16le",
            )
            .overwrite_output()
            .run(quiet=True)
        )

        segments = transcriber.transcribe_file(str(wav_path))
        return JSONResponse({"segments": segments, "file": file.filename})

    except Exception as exc:
        logger.error(f"File transcription error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        tmp_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
