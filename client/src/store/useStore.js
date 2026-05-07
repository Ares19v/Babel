import { create } from 'zustand'

const WS_URL = 'ws://localhost:8000/ws/stream'

export const useStore = create((set, get) => ({
  // Connection
  wsStatus: 'disconnected', // disconnected | connecting | ready | error
  ws: null,

  // Audio source
  source: 'mic', // mic | file | system
  setSource: (source) => set({ source }),

  // Transcription state
  subtitles: [],          // array of { id, text, language, langProb, timestamp, isFinal }
  currentSegment: '',     // live in-progress text
  detectedLanguage: null,
  latencyMs: null,

  // UI state
  isListening: false,
  isProcessingFile: false,
  fileSegments: [],       // full file transcription result

  // Actions
  connect: () => {
    const { wsStatus } = get()
    // Bail if already connected or mid-handshake
    if (wsStatus === 'ready' || wsStatus === 'connecting') return

    const existing = get().ws
    if (existing) existing.close()

    set({ wsStatus: 'connecting' })
    const socket = new WebSocket(WS_URL)

    socket.onopen = () => set({ ws: socket, wsStatus: 'connecting' })

    socket.onmessage = (evt) => {
      const data = JSON.parse(evt.data)
      get()._handleMessage(data)
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
    if (ws && wsStatus === 'ready') {
      ws.send(pcmBytes)
    }
  },

  sendReset: () => {
    const { ws } = get()
    if (ws) ws.send(JSON.stringify({ type: 'reset' }))
    set({ subtitles: [], currentSegment: '', detectedLanguage: null, latencyMs: null })
  },

  setListening: (v) => set({ isListening: v }),

  setFileSegments: (segs) => set({ fileSegments: segs, isProcessingFile: false }),
  setProcessingFile: (v) => set({ isProcessingFile: v }),

  _handleMessage: (data) => {
    switch (data.type) {
      case 'status':
        if (data.status === 'ready') set({ wsStatus: 'ready' })
        break

      case 'transcript': {
        const entry = {
          id: Date.now() + Math.random(),
          text: data.text,
          language: data.language,
          langProb: data.language_probability,
          words: data.words || [],
          timestamp: new Date(),
          isFinal: data.is_final,
        }
        set((state) => {
          const newSubs = [...state.subtitles]
          // If the last entry wasn't final, overwrite it with the new update
          if (newSubs.length > 0 && !newSubs[newSubs.length - 1].isFinal) {
            newSubs[newSubs.length - 1] = entry
          } else {
            newSubs.push(entry)
          }
          if (newSubs.length > 50) newSubs.shift()

          return {
            subtitles: newSubs,
            currentSegment: data.text,
            detectedLanguage: data.language,
            latencyMs: data.latency_ms,
          }
        })
        break
      }

      case 'pong':
        break

      case 'error':
        console.error('Server error:', data.message)
        break
    }
  },
}))
