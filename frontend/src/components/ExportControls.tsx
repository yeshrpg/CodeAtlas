import { useEffect, useRef, useState } from 'react'
import { copyMermaidCode } from '../lib/exportDiagram'

interface ExportControlsProps {
  /** Exact Mermaid source currently rendered; null when nothing to copy. */
  code: string | null
  /** Whether an SVG is currently rendered (controls Download availability). */
  canDownload: boolean
  onDownload: () => void
}

function ExportControls({ code, canDownload, onDownload }: ExportControlsProps) {
  const [copied, setCopied] = useState(false)
  const [showFallback, setShowFallback] = useState(false)
  const resetTimer = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (resetTimer.current !== null) {
        window.clearTimeout(resetTimer.current)
      }
    },
    [],
  )

  const handleCopy = async () => {
    if (!code) return
    const ok = await copyMermaidCode(code)
    if (ok) {
      setCopied(true)
      setShowFallback(false)
      if (resetTimer.current !== null) {
        window.clearTimeout(resetTimer.current)
      }
      resetTimer.current = window.setTimeout(() => setCopied(false), 1500)
    } else {
      // Clipboard unavailable/denied — show manual-copy textarea instead of
      // failing silently.
      setShowFallback(true)
    }
  }

  return (
    <div className="export-bar">
      <button
        type="button"
        className="analyze-button"
        onClick={() => void handleCopy()}
        disabled={!code}
      >
        {copied ? 'Copied!' : 'Copy Mermaid'}
      </button>
      <button
        type="button"
        className="analyze-button"
        onClick={onDownload}
        disabled={!canDownload}
        title={canDownload ? undefined : 'No diagram rendered yet'}
      >
        Download SVG
      </button>
      {showFallback && code && (
        <div className="copy-fallback">
          <p className="empty-note">
            Clipboard unavailable — copy the source manually:
          </p>
          <textarea
            className="copy-fallback-text"
            readOnly
            rows={8}
            value={code}
            onFocus={(e) => e.target.select()}
          />
        </div>
      )}
    </div>
  )
}

export default ExportControls
