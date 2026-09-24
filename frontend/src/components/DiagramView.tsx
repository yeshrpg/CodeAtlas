import { useEffect, useId, useRef, useState } from 'react'
import mermaid from 'mermaid'
import { toMermaid } from '../lib/toMermaid'
import {
  attachNodeClickListeners,
  buildNodeIndex,
} from '../lib/nodeMapping'
import type { Analysis } from '../types'

let mermaidInitialized = false

function ensureMermaidInitialized() {
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'neutral',
    })
    mermaidInitialized = true
  }
}

interface DiagramViewProps {
  analysis: Analysis
  onSelectComponent: (componentId: string) => void
}

function DiagramView({ analysis, onSelectComponent }: DiagramViewProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const rawId = useId()
  const renderCount = useRef(0)
  const svgContainerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false
    setSvg(null)
    setFailed(false)

    const render = async () => {
      try {
        ensureMermaidInitialized()
        const code = toMermaid(analysis?.components, analysis?.connections)
        renderCount.current += 1
        const renderId = `codeatlas_${rawId.replace(/[^A-Za-z0-9_]/g, '')}_${renderCount.current}`
        const { svg } = await mermaid.render(renderId, code)
        if (!cancelled) setSvg(svg)
      } catch {
        if (!cancelled) setFailed(true)
      }
    }

    void render()
    return () => {
      cancelled = true
    }
  }, [analysis, rawId])

  // Re-attach node click listeners after every successful render so they
  // always match the currently displayed SVG (no stale/duplicate listeners).
  useEffect(() => {
    const container = svgContainerRef.current
    if (!svg || !container) return undefined
    const index = buildNodeIndex(analysis?.components)
    const cleanup = attachNodeClickListeners(container, index, (componentId) => {
      console.log(`[CodeAtlas] node clicked: ${componentId}`)
      onSelectComponent(componentId)
    })
    return cleanup
  }, [svg, analysis, onSelectComponent])

  if (failed) {
    return (
      <section className="diagram-container" aria-label="Analysis fallback table">
        <p className="fallback-note">
          Diagram rendering failed — showing data as a table instead.
        </p>
        <h3>Components</h3>
        <table className="fallback-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Label</th>
              <th>Layer</th>
            </tr>
          </thead>
          <tbody>
            {(analysis?.components ?? []).map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.label}</td>
                <td>{c.layer}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Connections</h3>
        <table className="fallback-table">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {(analysis?.connections ?? []).map((conn, i) => (
              <tr key={`${conn.from}-${conn.to}-${i}`}>
                <td>{conn.from}</td>
                <td>{conn.to}</td>
                <td>{conn.weight}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    )
  }

  return (
    <section className="diagram-container" aria-label="Architecture diagram">
      {svg ? (
        <div ref={svgContainerRef} dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <p className="diagram-pending">Rendering diagram…</p>
      )}
    </section>
  )
}

export default DiagramView
