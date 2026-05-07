"""
AudioRingBuffer — thread-safe ring buffer for continuous PCM audio.

Design decisions:
- 30-second max window prevents memory bloat
- 3-second processing window with 0.5-second stride gives ~500ms latency
- ready_to_process() uses a stride counter so inference doesn't run every chunk
"""

import threading
import numpy as np


SAMPLE_RATE = 16_000
WINDOW_SECONDS = 3       # Reduced from 6 to 3 for snappy response
STRIDE_SECONDS = 0.5     
MIN_SPEECH_SECONDS = 0.5 


class AudioRingBuffer:
    def __init__(self, max_seconds: int = 30, sample_rate: int = SAMPLE_RATE):
        self.max_samples = max_seconds * sample_rate
        self.sample_rate = sample_rate
        self.window_samples = int(WINDOW_SECONDS * sample_rate)
        self.stride_samples = int(STRIDE_SECONDS * sample_rate)
        self.min_samples = int(MIN_SPEECH_SECONDS * sample_rate)

        self._buf: np.ndarray = np.zeros(0, dtype=np.float32)
        self._since_last_process = 0
        self._lock = threading.Lock()

    def push(self, audio: np.ndarray) -> None:
        """Append float32 PCM frames (already normalised to [-1, 1])."""
        with self._lock:
            self._buf = np.concatenate([self._buf, audio])
            # Trim to max window
            if len(self._buf) > self.max_samples:
                self._buf = self._buf[-self.max_samples:]
            self._since_last_process += len(audio)

    def ready_to_process(self) -> bool:
        with self._lock:
            return (
                self._since_last_process >= self.stride_samples
                and len(self._buf) >= self.min_samples
            )

    def get_window(self) -> np.ndarray:
        """Return the most recent WINDOW_SECONDS of audio and reset stride counter."""
        with self._lock:
            self._since_last_process = 0
            return self._buf[-self.window_samples:].copy()

    def reset(self) -> None:
        with self._lock:
            self._buf = np.zeros(0, dtype=np.float32)
            self._since_last_process = 0

    @property
    def buffered_seconds(self) -> float:
        with self._lock:
            return len(self._buf) / self.sample_rate
