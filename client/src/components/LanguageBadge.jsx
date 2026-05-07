import { motion, AnimatePresence } from 'framer-motion'
import { LANGUAGE_NAMES, LANGUAGE_FLAGS } from '../utils/languages'
import { useStore } from '../store/useStore'
import { Wifi, WifiOff, Zap } from 'lucide-react'

export function LanguageBadge() {
  const { detectedLanguage, latencyMs, wsStatus } = useStore()

  return (
    <div className="badge-row">
      {/* Connection status */}
      <motion.div
        className={`status-pill status-${wsStatus}`}
        layout
      >
        {wsStatus === 'ready' ? (
          <><Wifi size={12} /> Live</>
        ) : wsStatus === 'connecting' ? (
          <><span className="spinner-dot" /> Connecting</>
        ) : (
          <><WifiOff size={12} /> Offline</>
        )}
      </motion.div>

      {/* Detected language */}
      <AnimatePresence>
        {detectedLanguage && (
          <motion.div
            className="lang-badge"
            initial={{ opacity: 0, scale: 0.8, x: -10 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <span className="lang-flag">{LANGUAGE_FLAGS[detectedLanguage] || '🌐'}</span>
            <span className="lang-name">
              {LANGUAGE_NAMES[detectedLanguage] || detectedLanguage.toUpperCase()}
            </span>
            <span className="lang-arrow">→ EN</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Latency */}
      <AnimatePresence>
        {latencyMs !== null && (
          <motion.div
            className="latency-badge"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Zap size={11} />
            <span>{latencyMs}ms</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
