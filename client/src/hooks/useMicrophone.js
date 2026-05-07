import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '../store/useStore'

const SAMPLE_RATE = 16000
const CHUNK_DURATION_MS = 100 // send audio every 100ms

export function useMicrophone() {
  const { sendAudio, isListening, setListening, wsStatus } = useStore()
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
        },
      })
      streamRef.current = stream

      // Use whatever sample rate the browser gives us, then downsample to 16kHz
      const ctx = new AudioContext()
      ctxRef.current = ctx
      const nativeSR = ctx.sampleRate  // typically 44100 or 48000

      const source = ctx.createMediaStreamSource(stream)

      // bufferSize MUST be a power of 2 (256–16384)
      // 4096 at 44100Hz ≈ 93ms per chunk — good balance of latency vs overhead
      const processor = ctx.createScriptProcessor(4096, 1, 1)

      processor.onaudioprocess = (e) => {
        const float32 = e.inputBuffer.getChannelData(0)

        // Downsample from native rate to 16kHz
        const ratio = nativeSR / SAMPLE_RATE
        const outLen = Math.round(float32.length / ratio)
        const downsampled = new Float32Array(outLen)
        for (let i = 0; i < outLen; i++) {
          downsampled[i] = float32[Math.round(i * ratio)]
        }

        // Convert float32 [-1,1] → int16
        const int16 = new Int16Array(downsampled.length)
        for (let i = 0; i < downsampled.length; i++) {
          const s = Math.max(-1, Math.min(1, downsampled[i]))
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

  // Cleanup on unmount
  useEffect(() => () => stop(), [stop])

  return { start, stop }
}
