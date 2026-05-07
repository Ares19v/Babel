import { motion, AnimatePresence } from 'framer-motion'
import { Download, FileText } from 'lucide-react'
import { useStore } from '../store/useStore'
import { LANGUAGE_NAMES } from '../utils/languages'

function formatTime(seconds) {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

function exportSRT(segments) {
  const lines = segments.map((seg, i) => {
    const start = formatSRTTime(seg.start)
    const end = formatSRTTime(seg.end)
    return `${i + 1}\n${start} --> ${end}\n${seg.text}\n`
  })
  const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'babel_subtitles.srt'
  a.click()
  URL.revokeObjectURL(url)
}

function formatSRTTime(seconds) {
  const h = Math.floor(seconds / 3600).toString().padStart(2, '0')
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0')
  const s = Math.floor(seconds % 60).toString().padStart(2, '0')
  const ms = Math.round((seconds % 1) * 1000).toString().padStart(3, '0')
  return `${h}:${m}:${s},${ms}`
}

export function FileResults() {
  const { fileSegments, isProcessingFile } = useStore()

  if (isProcessingFile) {
    return (
      <div className="file-results">
        <div className="processing-indicator">
          <div className="spinner-large" />
          <span>Translating audio…</span>
        </div>
      </div>
    )
  }

  if (!fileSegments.length) return null

  const lang = fileSegments[0]?.language
  const totalDuration = fileSegments[fileSegments.length - 1]?.end || 0

  return (
    <AnimatePresence>
      <motion.div
        className="file-results"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="file-results-header">
          <div className="file-results-meta">
            <FileText size={16} />
            <span>{fileSegments.length} segments · {formatTime(totalDuration)}</span>
            {lang && (
              <span className="lang-chip">
                {LANGUAGE_NAMES[lang] || lang.toUpperCase()} → EN
              </span>
            )}
          </div>
          <button className="btn-export" onClick={() => exportSRT(fileSegments)}>
            <Download size={14} /> Export .srt
          </button>
        </div>

        <div className="segments-list">
          {fileSegments.map((seg, i) => (
            <motion.div
              key={i}
              className="segment-row"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.02, duration: 0.2 }}
            >
              <span className="seg-time">{formatTime(seg.start)}</span>
              <span className="seg-text">{seg.text}</span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
