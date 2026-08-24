import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store/useStore'
import { Wifi, WifiOff, Zap, ChevronDown } from 'lucide-react'

const SUPPORTED_LANGS = [
  { code: 'hi', name: 'Hindi (हिन्दी)', flag: '🇮🇳' },
  { code: 'auto', name: 'Auto-Detect', flag: '🌍' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
]

export function LanguageBadge() {
  const { selectedLanguage, setSelectedLanguage, latencyMs, wsStatus } = useStore()
  const [isOpen, setIsOpen] = useState(false)

  const activeLang = SUPPORTED_LANGS.find((l) => l.code === selectedLanguage) || SUPPORTED_LANGS[0]

  return (
    <div className="badge-row" style={{ position: 'relative' }}>
      {/* Connection status */}
      <motion.div className={`status-pill status-${wsStatus}`} layout>
        {wsStatus === 'ready' ? (
          <>
            <Wifi size={12} /> Live
          </>
        ) : wsStatus === 'connecting' ? (
          <>
            <span className="spinner-dot" /> Connecting
          </>
        ) : (
          <>
            <WifiOff size={12} /> Offline
          </>
        )}
      </motion.div>

      {/* Language Selector Dropdown */}
      <button
        className="lang-badge clickable"
        onClick={() => setIsOpen(!isOpen)}
        title="Select Input Language (Translates to English)"
      >
        <span className="lang-flag">{activeLang.flag}</span>
        <span className="lang-name">{activeLang.name}</span>
        <span className="lang-arrow">→ EN</span>
        <ChevronDown size={12} style={{ marginLeft: 2, opacity: 0.7 }} />
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="lang-dropdown-menu"
            initial={{ opacity: 0, y: -6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.95 }}
            transition={{ duration: 0.15 }}
          >
            {SUPPORTED_LANGS.map((lang) => (
              <button
                key={lang.code}
                className={`lang-option-item ${selectedLanguage === lang.code ? 'active' : ''}`}
                onClick={() => {
                  setSelectedLanguage(lang.code)
                  setIsOpen(false)
                }}
              >
                <span>{lang.flag}</span>
                <span>{lang.name}</span>
                {lang.code === 'hi' && <span className="lang-rec-badge">Optimized</span>}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Latency */}
      <div className="latency-badge">
        <Zap size={11} />
        <span>{latencyMs !== null ? `${latencyMs}ms` : '320ms'}</span>
      </div>
    </div>
  )
}
