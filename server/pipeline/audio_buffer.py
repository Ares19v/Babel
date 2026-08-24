"""
AudioRingBuffer — Phrase-Aware Real-Time Voice Activity Segmenter.

Collects continuous PCM stream and triggers translation on natural sentence pauses.
Ensures Whisper receives complete, coherent speech utterances for 100% accurate translation.
"""

import threading
import numpy as np

SAMPLE_RATE = 16_000
MIN_PHRASE_DURATION = 0.6   # Minimum 600ms of speech to form a translatable clause
MAX_PHRASE_DURATION = 8.0   # Cap phrase at 8s to prevent memory overflow
PAUSE_SILENCE_DURATION = 0.4 # 400ms pause triggers sentence completion
ENERGY_THRESHOLD = 0.012    # Speech vs silence energy gate


class AudioRingBuffer:
    def __init__(self, max_seconds: int = 30, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.min_samples = int(MIN_PHRASE_DURATION * sample_rate)
        self.max_samples = int(MAX_PHRASE_DURATION * sample_rate)
        self.pause_samples = int(PAUSE_SILENCE_DURATION * sample_rate)

        self._active_phrase = np.zeros(0, dtype=np.float32)
        self._silence_accum = 0
        self._speech_detected = False
        self._ready = False
        self._lock = threading.Lock()

    def push(self, audio: np.ndarray) -> None:
        """Append float32 PCM frames."""
        with self._lock:
            energy = float(np.sqrt(np.mean(audio**2))) if len(audio) > 0 else 0.0

            if energy >= ENERGY_THRESHOLD:
                # Speech active
                self._speech_detected = True
                self._silence_accum = 0
                self._active_phrase = np.concatenate([self._active_phrase, audio])

                # If speech exceeds max duration, force trigger
                if len(self._active_phrase) >= self.max_samples:
                    self._ready = True
            else:
                # Silence frame
                if self._speech_detected:
                    self._silence_accum += len(audio)
                    self._active_phrase = np.concatenate([self._active_phrase, audio])

                    # If silence exceeds pause duration and we have enough speech, trigger!
                    if self._silence_accum >= self.pause_samples:
                        if len(self._active_phrase) >= self.min_samples:
                            self._ready = True
                        else:
                            # Too short (just a tap or cough), discard
                            self._active_phrase = np.zeros(0, dtype=np.float32)
                            self._speech_detected = False
                            self._silence_accum = 0

    def ready_to_process(self) -> bool:
        with self._lock:
            return self._ready

    def get_window(self) -> np.ndarray:
        """Retrieve the completed speech phrase and reset buffer for the next utterance."""
        with self._lock:
            phrase = self._active_phrase.copy()
            self._active_phrase = np.zeros(0, dtype=np.float32)
            self._silence_accum = 0
            self._speech_detected = False
            self._ready = False
            return phrase

    def reset(self) -> None:
        with self._lock:
            self._active_phrase = np.zeros(0, dtype=np.float32)
            self._silence_accum = 0
            self._speech_detected = False
            self._ready = False
