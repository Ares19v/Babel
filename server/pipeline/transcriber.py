"""
GroqTranscriber — Real-time Multilingual → English Speech Translator.

Uses Groq's Whisper API (whisper-large-v3-turbo) which is:
- The official OpenAI model with REAL task="translations" support
- Returns 100% English text regardless of spoken language
- ~300ms per request, completely free tier

Audio is buffered in RAM, exported as in-memory WAV, and sent to Groq.
No disk writes needed for streaming.
"""

import io
import logging
import os
import re
import struct
import time
import threading
from typing import Optional

import numpy as np
from groq import Groq

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHANNELS = 1
SAMPLE_WIDTH = 2  # int16


def _build_wav_bytes(pcm_float32: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    Convert float32 numpy array to a valid in-memory WAV file (bytes).
    Groq accepts WAV, so we build it without writing to disk.
    """
    pcm_int16 = np.clip(pcm_float32, -1.0, 1.0)
    pcm_int16 = (pcm_int16 * 32767).astype(np.int16)
    raw_data = pcm_int16.tobytes()
    data_size = len(raw_data)
    file_size = 36 + data_size

    buf = io.BytesIO()
    # RIFF header
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', file_size))
    buf.write(b'WAVE')
    # fmt chunk
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))            # chunk size
    buf.write(struct.pack('<H', 1))             # PCM format
    buf.write(struct.pack('<H', CHANNELS))
    buf.write(struct.pack('<I', sample_rate))
    buf.write(struct.pack('<I', sample_rate * CHANNELS * SAMPLE_WIDTH))  # byte rate
    buf.write(struct.pack('<H', CHANNELS * SAMPLE_WIDTH))                # block align
    buf.write(struct.pack('<H', SAMPLE_WIDTH * 8))                       # bits per sample
    # data chunk
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(raw_data)
    return buf.getvalue()


# Common Whisper hallucination phrases to filter out
_HALLUCINATIONS = {
    "", ".", "..", "...", "!", "?",
    "you", "you.", "okay", "okay.",
    "thank you.", "thank you for watching.",
    "thanks for watching.", "goodbye.", "bye.",
    "subtitles by", "transcribed by",
    "♪", "♫",
}

# Non-Latin script detector (Devanagari, Arabic, CJK, etc.)
_NON_LATIN_RE = re.compile(r'[\u0900-\u097F\u0600-\u06FF\u3040-\u30FF\u4E00-\u9FFF\u0400-\u04FF]')


class StreamingTranscriber:
    """
    Multilingual → English translator using Groq Whisper API.
    task=translations always outputs English regardless of spoken language.
    """

    def __init__(
        self,
        model_size: str = "whisper-large-v3-turbo",
        device: str = "cuda",          # ignored, kept for API compat
        compute_type: str = "float16", # ignored, kept for API compat
        **kwargs,
    ):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment / .env")

        self._client = Groq(api_key=api_key)
        # Must use whisper-large-v3 — only Groq model supporting task=translations
        self._model = "whisper-large-v3"
        self._lock = threading.Lock()

        logger.info(f"Groq Whisper client initialized (model: {self._model}) → always outputs English")

    def set_forced_language(self, lang: Optional[str]) -> None:
        """No-op for Groq — it auto-detects and always outputs English translations."""
        logger.info(f"Language hint received: {lang!r} (Groq auto-detects; always translates to English)")

    def process_window(self, audio: np.ndarray) -> Optional[dict]:
        """Send audio phrase to Groq Whisper for English translation."""
        with self._lock:
            return self._infer(audio)

    def transcribe_file(self, audio_path: str, language: Optional[str] = None) -> list[dict]:
        """Translate a full audio file to English via Groq."""
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        try:
            t0 = time.perf_counter()
            response = self._client.audio.translations.create(
                file=("audio.wav", audio_bytes, "audio/wav"),
                model=self._model,
                response_format="verbose_json",
                temperature=0.0,
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            segments = []
            for seg in (getattr(response, "segments", None) or []):
                text = (seg.get("text") if isinstance(seg, dict) else seg.text or "").strip()
                if text:
                    segments.append({
                        "start": round(seg.get("start", 0) if isinstance(seg, dict) else seg.start, 2),
                        "end": round(seg.get("end", 0) if isinstance(seg, dict) else seg.end, 2),
                        "text": text,
                        "words": [],
                        "language": "auto",
                        "language_probability": 1.0,
                    })
            return segments
        except Exception as exc:
            logger.error(f"Groq file transcription error: {exc}")
            return []

    def reset(self) -> None:
        pass  # stateless

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def _infer(self, audio: np.ndarray) -> Optional[dict]:
        if len(audio) < 8000:  # < 0.5s
            return None

        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < 0.008:
            return None

        # Build in-memory WAV
        wav_bytes = _build_wav_bytes(audio)

        t0 = time.perf_counter()
        try:
            # task=translations → ALWAYS returns English
            response = self._client.audio.translations.create(
                file=("speech.wav", wav_bytes, "audio/wav"),
                model=self._model,
                response_format="verbose_json",
                temperature=0.0,
            )
        except Exception as exc:
            logger.error(f"Groq Whisper API error: {exc}")
            return None

        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Extract text
        text = (getattr(response, "text", None) or "").strip()

        if not text:
            return None

        # Filter known hallucinations
        if text.lower() in _HALLUCINATIONS or len(text) < 2:
            return None

        # Block any non-Latin script that somehow slipped through
        if _NON_LATIN_RE.search(text):
            logger.warning(f"Non-English text blocked: {text!r}")
            return None

        # Try to detect source language from verbose response
        detected_lang = "auto"
        try:
            segs = getattr(response, "segments", None) or []
            if segs:
                first = segs[0]
                detected_lang = (first.get("language") if isinstance(first, dict) else getattr(first, "language", "auto")) or "auto"
        except Exception:
            pass

        logger.info(f"[Groq] {detected_lang!r} → EN | {latency_ms}ms | {text!r}")

        return {
            "type": "transcript",
            "text": text,
            "language": detected_lang,
            "language_probability": 1.0,
            "words": [],
            "is_final": True,
            "latency_ms": latency_ms,
        }
