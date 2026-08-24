import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mic,
  MicOff,
  Upload,
  Radio,
  Copy,
  Check,
  Download,
  RotateCcw,
  Sparkles,
  Zap,
  Volume2,
  Cpu,
  Globe,
} from 'lucide-react'
import { AuroraBackground } from './components/AuroraBackground'
import { FileResults } from './components/FileResults'
import { useStore } from './store/useStore'
import { useMicrophone } from './hooks/useMicrophone'
import { useAudioFile } from './hooks/useAudioFile'
import { LANGUAGE_NAMES, LANGUAGE_FLAGS } from './utils/languages'

export default function App() {
  const {
    source,
    setSource,
    isListening,
    wsStatus,
    connect,
    sendReset,
    isProcessingFile,
    subtitles,
    detectedLanguage,
    latencyMs,
  } = useStore()

  const { start: startMic, stop: stopMic } = useMicrophone()
  const { transcribeFile } = useAudioFile()
  const fileRef = useRef(null)
  const [copied, setCopied] = useState(false)

  // Connect on mount
  useEffect(() => {
    const { connect } = useStore.getState()
    connect()
    const interval = setInterval(() => {
      const { wsStatus, connect } = useStore.getState()
      if (wsStatus === 'disconnected' || wsStatus === 'error') connect()
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleMicToggle = async () => {
    if (wsStatus === 'disconnected' || wsStatus === 'error') {
      connect()
      return
    }
    if (isListening) {
      stopMic()
    } else {
      await startMic()
    }
  }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    if (wsStatus !== 'ready') connect()
    await transcribeFile(file)
  }

  const handleCopyTranscript = () => {
    if (!subtitles.length) return
    const fullText = subtitles.map((s) => s.text).join(' ')
    navigator.clipboard.writeText(fullText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExportText = () => {
    if (!subtitles.length) return
    const fullText = subtitles.map((s) => `[${s.language || 'auto'}] ${s.text}`).join('\n')
    const blob = new Blob([fullText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `babel_translation_${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="babel-app-wrap">
      {/* Aurora Borealis Background */}
      <AuroraBackground />

      {/* Unified Center Workstation */}
      <div className="babel-card">
        {/* Top Header */}
        <header className="babel-header">
          <div className="brand-badge">
            <div className="brand-icon">
              <Sparkles size={16} />
            </div>
            <div>
              <span className="brand-title">BABEL</span>
              <span className="brand-subtitle">AI SPEECH TRANSLATOR</span>
            </div>
          </div>

          {/* Mode Switcher */}
          <div className="nav-tabs">
            <button
              className={`nav-tab ${source === 'mic' ? 'active' : ''}`}
              onClick={() => {
                setSource('mic')
                if (isListening) stopMic()
              }}
            >
              <Mic size={14} />
              <span>Live Microphone</span>
            </button>

            <button
              className={`nav-tab ${source === 'file' ? 'active' : ''}`}
              onClick={() => {
                setSource('file')
                if (isListening) stopMic()
              }}
            >
              <Upload size={14} />
              <span>File Upload</span>
            </button>

            <button
              className={`nav-tab ${source === 'system' ? 'active' : ''}`}
              onClick={() => {
                setSource('system')
                if (isListening) stopMic()
              }}
            >
              <Radio size={14} />
              <span>System Audio</span>
            </button>
          </div>

          {/* Status Badge */}
          <div className="header-status">
            {detectedLanguage && (
              <div className="lang-detected-pill">
                <span>{LANGUAGE_FLAGS[detectedLanguage] || '🌐'}</span>
                <span>{LANGUAGE_NAMES[detectedLanguage] || detectedLanguage.toUpperCase()}</span>
                <span className="arrow-en">➔ EN</span>
              </div>
            )}
            <div className={`status-dot-pill ${wsStatus}`}>
              <span className="status-indicator-dot" />
              <span>{wsStatus === 'ready' ? 'Ready' : wsStatus}</span>
            </div>
          </div>
        </header>

        {/* Central Translation Canvas */}
        <main className="babel-stage">
          {source === 'file' ? (
            <div className="file-view">
              <FileResults />
              {!isProcessingFile && (
                <div className="upload-dropzone" onClick={() => fileRef.current?.click()}>
                  <Upload size={32} color="#34d399" />
                  <div className="upload-title">Drop or browse audio / video file</div>
                  <div className="upload-sub">Supports MP3, MP4, WAV, MKV, M4A, WEBM</div>
                </div>
              )}
            </div>
          ) : (
            <div className="live-view">
              {/* Toolbar */}
              <div className="stage-toolbar">
                <div className="mic-status-label">
                  <span className={`pulse-dot ${isListening ? 'active' : ''}`} />
                  <span>
                    {isListening
                      ? 'Listening... Speak in Hindi or any language'
                      : 'Standby · Click start below to translate speech into English'}
                  </span>
                </div>

                <div className="stage-actions">
                  {subtitles.length > 0 && (
                    <>
                      <button className="tool-btn" onClick={handleCopyTranscript} title="Copy to clipboard">
                        {copied ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </button>

                      <button className="tool-btn" onClick={handleExportText} title="Download .txt transcript">
                        <Download size={13} />
                        <span>Export</span>
                      </button>
                    </>
                  )}

                  <button className="tool-btn danger" onClick={sendReset} title="Clear history">
                    <RotateCcw size={13} />
                    <span>Clear</span>
                  </button>
                </div>
              </div>

              {/* Subtitles Display Feed */}
              <div className="subtitles-feed">
                <AnimatePresence initial={false}>
                  {subtitles.map((entry, idx) => {
                    const isLatest = idx === subtitles.length - 1
                    return (
                      <motion.div
                        key={entry.id}
                        className={`subtitle-row ${isLatest ? 'current' : 'past'}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: isLatest ? 1 : 0.45, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <span className="subtitle-english-text">{entry.text}</span>
                      </motion.div>
                    )
                  })}
                </AnimatePresence>

                {subtitles.length === 0 && (
                  <div className="empty-state">
                    <Globe size={32} color="#34d399" style={{ opacity: 0.7 }} />
                    <div className="empty-text">
                      {isListening
                        ? 'Listening for speech... Speak in Hindi or any language'
                        : 'English subtitles will appear here as you speak'}
                    </div>
                  </div>
                )}
              </div>

              {/* Subtle Audio Waveform Indicator */}
              <div className="audio-visual-bar">
                <div className="wave-bars-container">
                  {Array.from({ length: 30 }).map((_, i) => (
                    <div
                      key={i}
                      className={`mini-bar ${isListening ? 'active' : ''}`}
                      style={{ animationDelay: `${(i % 8) * 0.08}s` }}
                    />
                  ))}
                </div>
                <div className="tech-badge">
                  <Volume2 size={12} color="#34d399" />
                  <span>16kHz Mono PCM · VAD Gated</span>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Bottom Action Footer */}
        <footer className="babel-footer">
          <input
            ref={fileRef}
            type="file"
            accept="audio/*,video/*"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />

          <div className="footer-left">
            <Cpu size={14} color="#34d399" />
            <span>NVIDIA RTX 5060 · Whisper Large-v3-Turbo</span>
          </div>

          <div className="footer-center">
            {source === 'mic' && (
              <button
                className={`main-action-btn ${isListening ? 'stop' : 'start'}`}
                onClick={handleMicToggle}
                disabled={wsStatus === 'connecting'}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                <span>{isListening ? 'Stop Listening' : 'Start Live Translation'}</span>
              </button>
            )}

            {source === 'file' && (
              <button
                className="main-action-btn start"
                onClick={() => fileRef.current?.click()}
                disabled={isProcessingFile}
              >
                <Upload size={18} />
                <span>{isProcessingFile ? 'Translating File...' : 'Choose File'}</span>
              </button>
            )}

            {source === 'system' && (
              <div className="system-pill">
                <Radio size={14} color="#38bdf8" />
                <span>WASAPI System Audio Capture Active</span>
              </div>
            )}
          </div>

          <div className="footer-right">
            <Zap size={14} color="#38bdf8" />
            <span>{latencyMs !== null ? `${latencyMs}ms latency` : 'CUDA FP16'}</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
