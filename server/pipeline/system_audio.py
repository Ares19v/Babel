"""
SystemAudioCapture — WASAPI loopback capture for Windows.

Captures whatever is playing through the PC speakers and streams it
over a local WebSocket to the Babel server. Run this as a separate
process/tray companion when "System Audio" mode is selected.

Requires PyAudioWPatch which extends PyAudio with WASAPI loopback support.
Install: pip install PyAudioWPatch
"""

import asyncio
import logging
import struct
import sys
import numpy as np
import websockets

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHUNK_DURATION_MS = 100   # 100ms chunks → ~10 sends/sec
BABEL_WS_URL = "ws://localhost:8000/ws/stream"


async def stream_system_audio(ws_url: str = BABEL_WS_URL):
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        print("ERROR: PyAudioWPatch not installed. Run: pip install PyAudioWPatch")
        sys.exit(1)

    pa = pyaudio.PyAudio()

    # Find the default WASAPI loopback device
    loopback_device = None
    wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
    default_speakers_idx = wasapi_info["defaultOutputDevice"]
    device_info = pa.get_device_info_by_index(default_speakers_idx)

    # Get the loopback device associated with the default speakers
    for i in range(pa.get_device_count()):
        d = pa.get_device_info_by_index(i)
        if d.get("isLoopbackDevice") and d["name"] == device_info["name"] + " [Loopback]":
            loopback_device = d
            loopback_idx = i
            break

    if loopback_device is None:
        print("ERROR: No WASAPI loopback device found. Enable 'Stereo Mix' in Windows Sound settings.")
        pa.terminate()
        sys.exit(1)

    channels = loopback_device["maxInputChannels"]
    native_rate = int(loopback_device["defaultSampleRate"])
    chunk_frames = int(native_rate * CHUNK_DURATION_MS / 1000)

    print(f"Capturing: {loopback_device['name']} @ {native_rate}Hz → resampling to {SAMPLE_RATE}Hz")

    async with websockets.connect(ws_url) as ws:
        print(f"Connected to Babel server at {ws_url}")

        def callback(in_data, frame_count, time_info, status):
            # Convert bytes → float32
            samples = np.frombuffer(in_data, dtype=np.int16)
            if channels == 2:
                # Stereo → mono
                samples = samples.reshape(-1, 2).mean(axis=1).astype(np.int16)

            # Resample to 16kHz if needed
            if native_rate != SAMPLE_RATE:
                from scipy.signal import resample_poly
                import math
                g = math.gcd(SAMPLE_RATE, native_rate)
                samples = resample_poly(samples, SAMPLE_RATE // g, native_rate // g).astype(np.int16)

            asyncio.get_event_loop().call_soon_threadsafe(
                send_queue.put_nowait, samples.tobytes()
            )
            return (None, pyaudio.paContinue)

        send_queue: asyncio.Queue = asyncio.Queue(maxsize=50)

        stream = pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=native_rate,
            input=True,
            input_device_index=loopback_idx,
            frames_per_buffer=chunk_frames,
            stream_callback=callback,
        )
        stream.start_stream()

        try:
            while stream.is_active():
                audio_bytes = await send_queue.get()
                await ws.send(audio_bytes)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(stream_system_audio())
