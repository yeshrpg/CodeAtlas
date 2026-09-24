import { useState } from 'react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import DemoDropdown from './components/DemoDropdown'
import ErrorBanner from './components/ErrorBanner'
import DiagramView from './components/DiagramView'
import SidePanel from './components/SidePanel'
import ConnectionsTable from './components/ConnectionsTable'
import { toL2Analysis } from './lib/subgraph'
import mockData from './mock/analysis.json'
import type { Analysis } from './types'
import './App.css'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [ref, setRef] = useState('')
  const [analysis, setAnalysis] = useState<Analysis>(
    mockData as unknown as Analysis,
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  )
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(
    null,
  )
  const [l2ComponentId, setL2ComponentId] = useState<string | null>(null)

  // Single entry point for new analysis data: resets selection and L2 view
  // so stale ids can never point at data that no longer exists.
  const replaceAnalysis = (data: Analysis) => {
    setAnalysis(data)
    setSelectedComponentId(null)
    setL2ComponentId(null)
  }

  // The backend analyze endpoint isn't available yet, so Analyze stubs
  // against the mock data (with a short simulated delay to exercise the
  // loading state). It feeds the same `analysis` state as the demo fetch.
  const handleAnalyze = () => {
    if (!repoUrl.trim()) {
      setValidationMessage('Please enter a repository URL.')
      return
    }
    setValidationMessage(null)
    setError(null)
    setLoading(true)
    window.setTimeout(() => {
      replaceAnalysis(mockData as unknown as Analysis)
      setLoading(false)
    }, 500)
  }

  const showHeuristicBadge = analysis.components.some(
    (c) => c.label_source === 'heuristic',
  )

  const labelOf = (componentId: string) =>
    analysis.components.find((c) => c.id === componentId)?.label ?? componentId

  // Stale selection (id with no matching data) resolves to null → panel
  // renders nothing instead of crashing.
  const selectedComponent =
    selectedComponentId === null
      ? null
      : (analysis.components.find((c) => c.id === selectedComponentId) ?? null)

  const displayAnalysis =
    l2ComponentId === null ? analysis : toL2Analysis(analysis, l2ComponentId)

  return (
    <main className="app">
      <Header
        repoUrl={repoUrl}
        ref={ref}
        loading={loading}
        validationMessage={validationMessage}
        onRepoUrlChange={(v) => {
          setRepoUrl(v)
          if (v.trim()) setValidationMessage(null)
        }}
        onRefChange={setRef}
        onAnalyze={handleAnalyze}
      />

      <div className="toolbar">
        <DemoDropdown
          loading={loading}
          onLoadingChange={setLoading}
          onResult={(data) => {
            setError(null)
            replaceAnalysis(data)
          }}
          onError={setError}
        />
        {loading && (
          <span className="spinner" role="status" aria-label="Loading">
            <span className="spinner-dot" />
            Loading…
          </span>
        )}
      </div>

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      )}

      <StatsBar stats={analysis.stats} showHeuristicBadge={showHeuristicBadge} />

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
            fileName={
              l2ComponentId === null
                ? 'codeatlas-diagram.svg'
                : `codeatlas-${l2ComponentId}.svg`
            }
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

      <section className="raw-data">
        <h2>Analysis data</h2>
        <pre>{JSON.stringify(analysis, null, 2)}</pre>
      </section>
    </main>
  )
}

export default App
