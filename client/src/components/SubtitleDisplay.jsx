import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store/useStore'

const MAX_VISIBLE = 4

export function SubtitleDisplay() {
  const { subtitles, isListening } = useStore()

  const visible = subtitles.slice(-MAX_VISIBLE)

  return (
    <div className="subtitle-stage">
      <div className="subtitle-scroll">
        <AnimatePresence initial={false} mode="popLayout">
          {visible.map((entry, idx) => {
            const isLatest = idx === visible.length - 1
            const opacity = 0.4 + (idx / (visible.length - 1 || 1)) * 0.6

            return (
              <motion.div
                key={entry.id}
                className={`subtitle-line ${isLatest ? 'latest' : 'historical'}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: isLatest ? 1 : opacity, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <span className="subtitle-text">{entry.text}</span>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {visible.length === 0 && (
          <div className="subtitle-placeholder">
            <span className="placeholder-icon">🎙️</span>
            <span>
              {isListening
                ? 'Listening... Speak in Hindi or any language to see English subtitles'
                : 'Click "Start Live Translation" and speak'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
