import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { AudioControls } from './components/AudioControls'
import { SubtitleDisplay } from './components/SubtitleDisplay'
import { LanguageBadge } from './components/LanguageBadge'
import { FileResults } from './components/FileResults'
import { useStore } from './store/useStore'

export default function App() {
  const { source } = useStore()

  // Connect once on mount. Retry every 3s by reading store state imperatively
  // (NOT as a dependency — that caused an infinite reconnect loop)
  useEffect(() => {
    const { connect } = useStore.getState()
    connect()
    const interval = setInterval(() => {
      const { wsStatus, connect } = useStore.getState()
      if (wsStatus === 'disconnected' || wsStatus === 'error') connect()
    }, 3000)
    return () => clearInterval(interval)
  }, []) // empty — run exactly once on mount

  return (
    <div className="app">
      {/* Animated background orbs */}
      <div className="bg-orb orb-1" />
      <div className="bg-orb orb-2" />
      <div className="bg-orb orb-3" />

      {/* Header */}
      <motion.header
        className="header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">Babel</span>
          <span className="logo-sub">Real-Time Translation</span>
        </div>
        <LanguageBadge />
      </motion.header>

      {/* Main content */}
      <main className="main">
        {/* Subtitle stage (only for live mic/system mode) */}
        {(source === 'mic' || source === 'system') && (
          <motion.div
            className="card subtitle-card"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <SubtitleDisplay />
          </motion.div>
        )}

        {/* File results */}
        {source === 'file' && (
          <motion.div
            className="card file-card"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <FileResults />
          </motion.div>
        )}

        {/* Controls */}
        <motion.div
          className="card controls-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <AudioControls />
        </motion.div>
      </main>

      <footer className="footer">
        <span>Powered by Whisper large-v3-turbo · LoRA fine-tuned on FLEURS hi_in</span>
        <span className="footer-sep">·</span>
        <span>RTX 5060 · CUDA fp16</span>
      </footer>
    </div>
  )
}
