import { useState } from 'react'
import DiagramView from './DiagramView'
import SidePanel from './SidePanel'
import ConnectionsTable from './ConnectionsTable'
import { toL2Analysis } from '../lib/subgraph'
import mockCompare from '../mock/compare.json'
import type { AnalysisConnection, CompareResponse } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

interface CompareViewProps {
  loading: boolean
  onLoadingChange: (loading: boolean) => void
  onError: (message: string) => void
}

function connKey(c: AnalysisConnection, i: number) {
  return `${c?.from}-${c?.to}-${i}`
}

function connLabel(c: AnalysisConnection) {
  return `${c.from} → ${c.to} (weight: ${c.weight})`
}

function CompareView({ loading, onLoadingChange, onError }: CompareViewProps) {
  const [baseUrl, setBaseUrl] = useState('')
  const [baseRef, setBaseRef] = useState('')
  const [headUrl, setHeadUrl] = useState('')
  const [headRef, setHeadRef] = useState('')
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  )
  const [result, setResult] = useState<CompareResponse | null>(null)
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(
    null,
  )
  const [l2ComponentId, setL2ComponentId] = useState<string | null>(null)

  const handleCompare = async () => {
    if (!baseUrl.trim() || !headUrl.trim()) {
      setValidationMessage('Please enter both base and head repository URLs.')
      return
    }
    setValidationMessage(null)
    onLoadingChange(true)
    try {
      const res = await fetch(`${API_URL}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base: { repo_url: baseUrl.trim(), ref: baseRef.trim() || undefined },
          head: { repo_url: headUrl.trim(), ref: headRef.trim() || undefined },
        }),
      })
      if (!res.ok) {
        onError(`Compare request failed: ${res.status} ${res.statusText}`)
        return
      }
      const data = (await res.json()) as CompareResponse
      setResult(data)
      setSelectedComponentId(null)
      setL2ComponentId(null)
    } catch (err) {
      onError(
        err instanceof Error
          ? `Compare request failed: ${err.message}`
          : 'Compare request failed: unknown error',
      )
    } finally {
      onLoadingChange(false)
    }
  }

  // No /compare endpoint exists yet, so verify the full flow against mock data.
  const handleUseMock = () => {
    setValidationMessage(null)
    setResult(mockCompare as unknown as CompareResponse)
    setSelectedComponentId(null)
    setL2ComponentId(null)
  }

  const analysis = result?.analysis ?? null
  const labelOf = (componentId: string) =>
    analysis?.components.find((c) => c.id === componentId)?.label ??
    componentId
  const selectedComponent =
    analysis && selectedComponentId !== null
      ? (analysis.components.find((c) => c.id === selectedComponentId) ?? null)
      : null
  const displayAnalysis =
    analysis === null || l2ComponentId === null
      ? analysis
      : toL2Analysis(analysis, l2ComponentId)

  const addedComponents = Array.isArray(result?.added_components)
    ? result.added_components
    : []
  const removedComponents = Array.isArray(result?.removed_components)
    ? result.removed_components
    : []
  const addedConnections = Array.isArray(result?.added_connections)
    ? result.added_connections
    : []
  const removedConnections = Array.isArray(result?.removed_connections)
    ? result.removed_connections
    : []
  const readingOrder = Array.isArray(result?.reading_order)
    ? result.reading_order
    : []
  const hasChanges =
    addedComponents.length +
      removedComponents.length +
      addedConnections.length +
      removedConnections.length >
    0

  return (
    <div className="compare-view">
      <div className="compare-form">
        <fieldset>
          <legend>Base</legend>
          <input
            type="text"
            className="text-input"
            placeholder="Base repo URL"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            disabled={loading}
          />
          <input
            type="text"
            className="text-input ref-input"
            placeholder="Ref (optional)"
            value={baseRef}
            onChange={(e) => setBaseRef(e.target.value)}
            disabled={loading}
          />
        </fieldset>
        <fieldset>
          <legend>Head</legend>
          <input
            type="text"
            className="text-input"
            placeholder="Head repo URL"
            value={headUrl}
            onChange={(e) => setHeadUrl(e.target.value)}
            disabled={loading}
          />
          <input
            type="text"
            className="text-input ref-input"
            placeholder="Ref (optional)"
            value={headRef}
            onChange={(e) => setHeadRef(e.target.value)}
            disabled={loading}
          />
        </fieldset>
      </div>
      {validationMessage && (
        <p className="validation-message" role="alert">
          {validationMessage}
        </p>
      )}
      <div className="toolbar">
        <button
          type="button"
          className="analyze-button"
          onClick={() => void handleCompare()}
          disabled={loading}
        >
          {loading ? 'Comparing…' : 'Compare'}
        </button>
        <button
          type="button"
          className="analyze-button"
          onClick={handleUseMock}
          disabled={loading}
        >
          Use mock data
        </button>
      </div>

      {result && analysis && displayAnalysis && (
        <>
          {l2ComponentId !== null && (
            <div className="l2-bar">
              <span>
                Detail view: <strong>{labelOf(l2ComponentId)}</strong>
              </span>
              <button
                type="button"
                className="analyze-button"
                onClick={() => setL2ComponentId(null)}
              >
                ← Back to full diagram
              </button>
            </div>
          )}

          <div className="content-row">
            <div className="diagram-column">
              <DiagramView
                analysis={displayAnalysis}
                onSelectComponent={setSelectedComponentId}
                fileName="codeatlas-compare.svg"
              />
              <ConnectionsTable
                connections={displayAnalysis.connections}
                labelOf={labelOf}
              />
            </div>
            {selectedComponent && (
              <SidePanel
                key={selectedComponent.id}
                component={selectedComponent}
                connections={analysis.connections}
                labelOf={labelOf}
                onClose={() => setSelectedComponentId(null)}
                onOpenDetailView={setL2ComponentId}
              />
            )}
          </div>

          <section className="diff-section" aria-label="Differences">
            <h2>Changes</h2>
            {!hasChanges && <p className="empty-note">no changes</p>}
            {addedComponents.length > 0 && (
              <>
                <h3>Added components</h3>
                <ul className="diff-added">
                  {addedComponents.map((id) => (
                    <li key={id}>{labelOf(id)}</li>
                  ))}
                </ul>
              </>
            )}
            {removedComponents.length > 0 && (
              <>
                <h3>Removed components</h3>
                <ul className="diff-removed">
                  {removedComponents.map((id) => (
                    <li key={id}>{labelOf(id)}</li>
                  ))}
                </ul>
              </>
            )}
            {addedConnections.length > 0 && (
              <>
                <h3>Added connections</h3>
                <ul className="diff-added">
                  {addedConnections.map((c, i) => (
                    <li key={connKey(c, i)}>{connLabel(c)}</li>
                  ))}
                </ul>
              </>
            )}
            {removedConnections.length > 0 && (
              <>
                <h3>Removed connections</h3>
                <ul className="diff-removed">
                  {removedConnections.map((c, i) => (
                    <li key={connKey(c, i)}>{connLabel(c)}</li>
                  ))}
                </ul>
              </>
            )}
          </section>

          {readingOrder.length > 0 && (
            <section className="reading-order" aria-label="Reading order">
              <h2>Reading order</h2>
              <ol>
                {readingOrder.map((id) => (
                  <li key={id}>{labelOf(id)}</li>
                ))}
              </ol>
            </section>
          )}
        </>
      )}
    </div>
  )
}

export default CompareView
