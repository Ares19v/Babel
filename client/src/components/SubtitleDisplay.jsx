import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '../store/useStore'

// Display the last N subtitle entries as a rolling feed
const MAX_VISIBLE = 5

export function SubtitleDisplay() {
  const { subtitles, currentSegment, detectedLanguage } = useStore()

  const visible = subtitles.slice(-MAX_VISIBLE)

  return (
    <div className="subtitle-stage">
      <div className="subtitle-scroll">
        <AnimatePresence initial={false} mode="popLayout">
          {visible.map((entry, idx) => {
            const isLatest = idx === visible.length - 1
            const opacity = 0.3 + (idx / (visible.length - 1 || 1)) * 0.7

            return (
              <motion.div
                key={entry.id}
                className="subtitle-line"
                initial={{ opacity: 0, y: 20, scale: 0.97 }}
                animate={{ opacity: isLatest ? 1 : opacity, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.95 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                {isLatest ? (
                  <WordByWord words={entry.words} text={entry.text} />
                ) : (
                  <span className="subtitle-text faded">{entry.text}</span>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>

        {visible.length === 0 && (
          <motion.div
            className="subtitle-placeholder"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <span className="placeholder-icon">🌐</span>
            <span>Start speaking — English subtitles will appear here</span>
          </motion.div>
        )}
      </div>
    </div>
  )
}

// Animate words appearing one by one using their timestamps
function WordByWord({ words, text }) {
  if (!words || words.length === 0) {
    return <span className="subtitle-text">{text}</span>
  }

  return (
    <span className="subtitle-text">
      {words.map((w, i) => (
        <motion.span
          key={i}
          className="subtitle-word"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15, delay: i * 0.03 }}
        >
          {w.word}
        </motion.span>
      ))}
    </span>
  )
}
