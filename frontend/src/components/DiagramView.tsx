import { useEffect, useId, useRef, useState } from 'react'
import mermaid from 'mermaid'
import { toMermaid } from '../lib/toMermaid'
import {
  resolveDiagramSource,
  type FallbackTables,
} from '../lib/diagramSource'
import {
  attachNodeClickListeners,
  buildNodeIndex,
} from '../lib/nodeMapping'
import {
  applyHealthStyling,
  hasHealthIssues,
} from '../lib/applyHealthStyling'
import { downloadBlob, serializeSvgToBlob } from '../lib/exportDiagram'
import ExportControls from './ExportControls'
import { HealthIssuesPanel } from './HealthIssuesPanel'
import type { Analysis, AnalysisHealth } from '../types'

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
  /** Download file name (App makes it L1/L2-aware). */
  fileName: string
  /**
   * Stage B2 real-backend path. `undefined` (default) = legacy mode: Mermaid
   * is generated locally from `analysis` via toMermaid (Compare tab and the
   * pre-analyze default — unchanged). A string is rendered directly via
   * `mermaid.render()` with no conversion. `null` means the backend produced
   * no diagram → empty state, never a crash.
   */
  mermaidSource?: string | null
  /**
   * Real-shape rows for the fallback table when a direct render fails, so it
   * shows real data instead of stale mock data. Omit in legacy mode.
   */
  realFallback?: FallbackTables | null
  /**
   * Optional architecture-health report (backend `health` field). When
   * undefined/null/empty the diagram renders exactly as without it —
   * this prop only ever adds styling + a summary badge, never changes
   * the base render or node-click behavior.
   */
  health?: AnalysisHealth | null
}

function DiagramView({
  analysis,
  onSelectComponent,
  fileName,
  mermaidSource,
  realFallback,
  health,
}: DiagramViewProps) {
  const [svg, setSvg] = useState<string | null>(null)
  const [code, setCode] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const [empty, setEmpty] = useState(false)
  const rawId = useId()
  const renderCount = useRef(0)
  const svgContainerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false
    setSvg(null)
    setCode(null)
    setFailed(false)
    setEmpty(false)

    const render = async () => {
      try {
        ensureMermaidInitialized()
        const source = resolveDiagramSource(mermaidSource)
        if (source.kind === 'empty') {
          if (!cancelled) setEmpty(true)
          return
        }
        // Legacy mode generates locally; direct mode renders the backend's
        // `mermaid.source` verbatim — no conversion step either way here.
        const code =
          source.kind === 'direct'
            ? source.code
            : toMermaid(analysis?.components, analysis?.connections)
        renderCount.current += 1
        const renderId = `codeatlas_${rawId.replace(/[^A-Za-z0-9_]/g, '')}_${renderCount.current}`
        const { svg } = await mermaid.render(renderId, code)
        if (!cancelled) {
          setSvg(svg)
          setCode(code)
        }
      } catch {
        if (!cancelled) setFailed(true)
      }
    }

    void render()
    return () => {
      cancelled = true
    }
  }, [analysis, mermaidSource, rawId])

  // Re-attach node click listeners after every successful render so they
  // always match the currently displayed SVG (no stale/duplicate listeners).
  // In direct mode (real backend `mermaid.source`) the legacy mock index is
  // inapplicable by design, so listeners attach quiet — otherwise every
  // node would log a "no matching component" warning.
  useEffect(() => {
    const container = svgContainerRef.current
    if (!svg || !container) return undefined
    const index = buildNodeIndex(analysis?.components)
    const cleanup = attachNodeClickListeners(
      container,
      index,
      (componentId) => {
        onSelectComponent(componentId)
      },
      { quiet: mermaidSource !== undefined },
    )
    return cleanup
  }, [svg, analysis, onSelectComponent, mermaidSource])

  // Health-flags overlay (dead nodes grey/dashed, cycle edges red/bold).
  // Strictly additive: skipped entirely when health is absent/empty, runs
  // after click-listener attachment, and never touches click behavior.
  // applyHealthStyling is internally try/catch-guarded and returns its own
  // cleanup, so a failure here can never break the base diagram.
  useEffect(() => {
    const container = svgContainerRef.current
    if (!svg || !container) return undefined
    if (!hasHealthIssues(health)) return undefined
    return applyHealthStyling(container, health, code)
  }, [svg, code, health])

  const handleDownload = () => {
    const svgElement = svgContainerRef.current?.querySelector('svg')
    if (!svgElement) return
    downloadBlob(serializeSvgToBlob(svgElement), fileName)
  }

  // Low-weight warning badge next to the Copy Mermaid control. Shown only
  // when health flags exist AND the backend supplied a summary string —
  // the summary is rendered verbatim. Otherwise null: zero DOM/layout
  // change versus today's rendering.
  const showHealthBadge =
    hasHealthIssues(health) &&
    typeof health?.summary === 'string' &&
    health.summary.length > 0

  if (failed) {
    // Direct-render failure on a real analysis shows real rows; legacy mode
    // keeps the previous mock-shape tables.
    const fallbackComponents =
      realFallback?.components ?? analysis?.components ?? []
    const fallbackConnections =
      realFallback?.connections ?? analysis?.connections ?? []
    return (
      <section className="diagram-container" aria-label="Analysis fallback table">
        <ExportControls code={null} canDownload={false} onDownload={() => {}} />
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
            {fallbackComponents.map((c) => (
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
            {fallbackConnections.map((conn, i) => (
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

  if (empty) {
    return (
      <section className="diagram-container" aria-label="Architecture diagram">
        <ExportControls code={null} canDownload={false} onDownload={() => {}} />
        <p className="empty-note">
          No diagram was produced for this analysis — data is still available
          in the tables below.
        </p>
      </section>
    )
  }

  return (
    <section className="diagram-container" aria-label="Architecture diagram">
      <ExportControls code={code} canDownload={svg !== null} onDownload={handleDownload} />
      {showHealthBadge ? (
        <p className="health-badge" role="status">
          {health?.summary}
        </p>
      ) : null}
      {svg ? (
        <div ref={svgContainerRef} dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <p className="diagram-pending">Rendering diagram…</p>
      )}
      <HealthIssuesPanel health={health} />
    </section>
  )
}

export default DiagramView
