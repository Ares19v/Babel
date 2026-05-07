import { motion } from 'framer-motion'
import { Mic, MicOff, Upload, Monitor, RotateCcw } from 'lucide-react'
import { useStore } from '../store/useStore'
import { useMicrophone } from '../hooks/useMicrophone'
import { useAudioFile } from '../hooks/useAudioFile'
import { useRef } from 'react'

export function AudioControls() {
  const { source, setSource, isListening, wsStatus, connect, sendReset, isProcessingFile } = useStore()
  const { start: startMic, stop: stopMic } = useMicrophone()
  const { transcribeFile } = useAudioFile()
  const fileRef = useRef(null)

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

  return (
    <div className="controls-bar">
      {/* Source selector */}
      <div className="source-tabs">
        {['mic', 'file', 'system'].map((s) => (
          <button
            key={s}
            className={`source-tab ${source === s ? 'active' : ''}`}
            onClick={() => {
              setSource(s)
              if (isListening) stopMic()
            }}
          >
            {s === 'mic' && <Mic size={14} />}
            {s === 'file' && <Upload size={14} />}
            {s === 'system' && <Monitor size={14} />}
            <span>{s === 'mic' ? 'Microphone' : s === 'file' ? 'File' : 'System Audio'}</span>
          </button>
        ))}
      </div>

      <div className="controls-actions">
        {/* Main action button */}
        {source === 'mic' && (
          <motion.button
            className={`btn-main ${isListening ? 'btn-stop' : 'btn-start'}`}
            onClick={handleMicToggle}
            disabled={wsStatus === 'connecting'}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            {isListening ? (
              <><MicOff size={18} /> Stop</>
            ) : (
              <><Mic size={18} /> {wsStatus === 'ready' ? 'Start Listening' : 'Connect & Listen'}</>
            )}
            {isListening && <PulseRing />}
          </motion.button>
        )}

        {source === 'file' && (
          <>
            <input
              ref={fileRef}
              type="file"
              accept="audio/*,video/*"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <motion.button
              className="btn-main btn-start"
              onClick={() => fileRef.current?.click()}
              disabled={isProcessingFile}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
            >
              {isProcessingFile ? (
                <><span className="spinner" /> Translating…</>
              ) : (
                <><Upload size={18} /> Upload File</>
              )}
            </motion.button>
          </>
        )}

        {source === 'system' && (
          <div className="system-notice">
            <Monitor size={16} />
            <span>Run <code>python server/pipeline/system_audio.py</code> in terminal</span>
          </div>
        )}

        {/* Reset */}
        <motion.button
          className="btn-icon"
          onClick={sendReset}
          title="Clear subtitles"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <RotateCcw size={16} />
        </motion.button>
      </div>
    </div>
  )
}

function PulseRing() {
  return (
    <motion.span
      className="pulse-ring"
      animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    />
  )
}
