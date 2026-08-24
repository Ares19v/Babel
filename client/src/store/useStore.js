import { create } from 'zustand'

const WS_URL = 'ws://localhost:8000/ws/stream'

export const useStore = create((set, get) => ({
  // Connection
  wsStatus: 'disconnected',
  ws: null,

  // Audio source
  source: 'mic',
  setSource: (source) => set({ source }),

  // Transcription state
  subtitles: [],
  detectedLanguage: null,
  latencyMs: null,
  // ALWAYS 'auto' — never force source language.
  // Whisper task="translate" auto-detects source and always outputs English.
  selectedLanguage: 'auto',
  lastSubtitleTime: 0,

  // UI state
  isListening: false,
  isProcessingFile: false,
  fileSegments: [],

  // Actions
  connect: () => {
    const { wsStatus } = get()
    if (wsStatus === 'ready' || wsStatus === 'connecting') return

    const existing = get().ws
    if (existing) existing.close()

    set({ wsStatus: 'connecting' })
    const socket = new WebSocket(WS_URL)

    socket.onopen = () => {
      set({ ws: socket, wsStatus: 'ready' })
      // NEVER send set_language — always let Whisper auto-detect
      // so task="translate" works correctly and outputs English subtitles
    }

    socket.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        get()._handleMessage(data)
      } catch (e) {
        // ignore
      }
    }

    socket.onerror = () => set({ wsStatus: 'error' })
    socket.onclose = () => set({ wsStatus: 'disconnected', ws: null, isListening: false })
  },

  disconnect: () => {
    const { ws } = get()
    if (ws) ws.close()
    set({ ws: null, wsStatus: 'disconnected', isListening: false })
  },

  sendAudio: (pcmBytes) => {
    const { ws, wsStatus } = get()
    if (ws && wsStatus === 'ready' && ws.readyState === WebSocket.OPEN) {
      ws.send(pcmBytes)
    }
  },

  sendReset: () => {
    const { ws } = get()
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'reset' }))
    }
    set({ subtitles: [], detectedLanguage: null, latencyMs: null, lastSubtitleTime: 0 })
  },

  setListening: (v) => set({ isListening: v }),
  setFileSegments: (segs) => set({ fileSegments: segs, isProcessingFile: false }),
  setProcessingFile: (v) => set({ isProcessingFile: v }),

  _handleMessage: (data) => {
    switch (data.type) {
      case 'status':
        if (data.status === 'ready' || data.status === 'language_updated') {
          set({ wsStatus: 'ready' })
        }
        break

      case 'transcript': {
        const text = data.text?.trim()
        if (!text) return

        const now = Date.now()
        const { subtitles, lastSubtitleTime } = get()
        const timeSinceLast = now - lastSubtitleTime

        const entry = {
          id: now + Math.random(),
          text: text,
          language: data.language,
          langProb: data.language_probability,
          timestamp: new Date(),
        }

        let newSubs = [...subtitles]

        // New subtitle line after 2s pause, otherwise update active line
        if (newSubs.length === 0 || timeSinceLast > 2000) {
          newSubs.push(entry)
        } else {
          newSubs[newSubs.length - 1] = entry
        }

        if (newSubs.length > 30) newSubs.shift()

        set({
          subtitles: newSubs,
          detectedLanguage: data.language,
          latencyMs: data.latency_ms,
          lastSubtitleTime: now,
        })
        break
      }

      case 'pong':
        break

      default:
        break
    }
  },
}))
