import { useCallback } from 'react'
import { useStore } from '../store/useStore'

const API_URL = 'http://localhost:8000'

export function useAudioFile() {
  const { setFileSegments, setProcessingFile } = useStore()

  const transcribeFile = useCallback(async (file) => {
    setProcessingFile(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_URL}/transcribe/file`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'File transcription failed')
      }

      const data = await res.json()
      setFileSegments(data.segments || [])
      return data
    } catch (err) {
      console.error('File transcription error:', err)
      setProcessingFile(false)
      throw err
    }
  }, [setFileSegments, setProcessingFile])

  return { transcribeFile }
}
