import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '../store/useStore'

const TARGET_SAMPLE_RATE = 16000

/**
 * Linear interpolation downsampler — avoids aliasing artifacts
 * that cause Whisper to emit garbage tokens or wrong-language output.
 */
function downsampleLinear(float32, fromRate, toRate) {
  if (fromRate === toRate) return float32
  const ratio = fromRate / toRate
  const outLen = Math.floor(float32.length / ratio)
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const pos = i * ratio
    const idx = Math.floor(pos)
    const frac = pos - idx
    const a = float32[idx] ?? 0
    const b = float32[idx + 1] ?? a
    out[i] = a + frac * (b - a)
  }
  return out
}

export function useMicrophone() {
  const { sendAudio, setListening, wsStatus } = useStore()
  const streamRef = useRef(null)
  const processorRef = useRef(null)
  const ctxRef = useRef(null)

  const start = useCallback(async () => {
    if (wsStatus !== 'ready') return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: TARGET_SAMPLE_RATE },
        },
      })
      streamRef.current = stream

      // Request 16kHz directly from the browser — Chrome/Edge support this
      // Fallback: AudioContext will use native rate and we downsample cleanly
      const ctx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })
      ctxRef.current = ctx
      const nativeSR = ctx.sampleRate

      const source = ctx.createMediaStreamSource(stream)

      // 4096 samples at 16kHz = 256ms per chunk — good latency vs overhead
      const processor = ctx.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        const float32 = e.inputBuffer.getChannelData(0)

        // Downsample if needed (usually nativeSR === 16000 now)
        const resampled = nativeSR !== TARGET_SAMPLE_RATE
          ? downsampleLinear(float32, nativeSR, TARGET_SAMPLE_RATE)
          : float32

        // Convert float32 [-1,1] → int16 PCM
        const int16 = new Int16Array(resampled.length)
        for (let i = 0; i < resampled.length; i++) {
          const s = Math.max(-1, Math.min(1, resampled[i]))
          int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }
        sendAudio(int16.buffer)
      }

      source.connect(processor)
      processor.connect(ctx.destination)
      processorRef.current = processor

      setListening(true)
    } catch (err) {
      console.error('Microphone access error:', err)
    }
  }, [wsStatus, sendAudio, setListening])

  const stop = useCallback(() => {
    processorRef.current?.disconnect()
    ctxRef.current?.close()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    processorRef.current = null
    ctxRef.current = null
    setListening(false)
  }, [setListening])

  useEffect(() => () => stop(), [stop])

  return { start, stop }
}
