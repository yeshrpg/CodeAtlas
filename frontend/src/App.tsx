import { useEffect, useState } from 'react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import DemoDropdown from './components/DemoDropdown'
import ErrorBanner from './components/ErrorBanner'
import DiagramView from './components/DiagramView'
import CompareView from './components/CompareView'
import SidePanel from './components/SidePanel'
import ComponentList from './components/ComponentList'
import ConnectionsTable from './components/ConnectionsTable'
import UnresolvedImports from './components/UnresolvedImports'
import RepoHeader from './components/RepoHeader'
import { toL2Analysis } from './lib/subgraph'
import { toFallbackRows } from './lib/diagramSource'
import { buildLabelMap, labelOfId } from './lib/realDrilldown'
import {
  INVALID_REPO_MESSAGE,
  analyzeRepo,
  analyzeResultError,
  parseRepoUrl,
  wakeBackend,
} from './lib/api'
import mockData from './mock/analysis.json'
import type { Analysis, AnalysisResult } from './types'
import './App.css'

/** Reassuring status line for the 10-60s+ analyze wait, driven by elapsed time. */
function analyzeStatusMessage(elapsedSec: number): string {
  if (elapsedSec < 15) return 'Cloning repo and scanning files…'
  if (elapsedSec < 35)
    return 'Still working — parsing imports and building components…'
  return 'Almost there — large repos can take up to a minute…'
}

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
  // Stage B3: list-driven selection for real analyses (replaces node-click).
  const [selectedRealId, setSelectedRealId] = useState<string | null>(null)
  const [l2ComponentId, setL2ComponentId] = useState<string | null>(null)
  const [view, setView] = useState<'analyze' | 'compare'>('analyze')
  // Stage B1: full real-backend result, stored for B2/B3 to render.
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null,
  )
  const [analyzeElapsedSec, setAnalyzeElapsedSec] = useState(0)

  // Single entry point for new analysis data: resets selection and L2 view
  // so stale ids can never point at data that no longer exists.
  const replaceAnalysis = (data: Analysis) => {
    setAnalysis(data)
    setSelectedComponentId(null)
    setL2ComponentId(null)
  }

  // Wake the (cold-starting) backend once on page load. Non-blocking and
  // silent by design — never gates the UI.
  useEffect(() => {
    wakeBackend()
  }, [])

  // Elapsed-seconds ticker while an analyze request is in flight, so the
  // loading state reassures during the 10-60s+ wait.
  useEffect(() => {
    if (!loading) return
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      setAnalyzeElapsedSec(Math.floor((Date.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [loading])

  // Real backend flow (Stage B1): one synchronous POST /analyze with a
  // >=120s timeout. Button is disabled via `loading` for the whole request
  // to prevent double-submit against the tight Gemini rate limit.
  const handleAnalyze = async () => {
    if (loading) return
    if (!repoUrl.trim()) {
      setValidationMessage('Please enter a repository URL.')
      return
    }
    const parsed = parseRepoUrl(repoUrl)
    if (!parsed) {
      setValidationMessage(
        'Could not parse that URL — use https://github.com/owner/repo or owner/repo.',
      )
      return
    }
    setValidationMessage(null)
    setError(null)
    setAnalyzeElapsedSec(0)
    setLoading(true)
    try {
      const result = await analyzeRepo(parsed.owner, parsed.name, ref)
      const failureMessage = analyzeResultError(result)
      if (failureMessage !== null) {
        // status "failed" — show the backend's error string verbatim.
        setError(failureMessage)
        return
      }
      // status "done" (pending/running stored as-is) — rendering is B2/B3.
      setAnalysisResult(result)
      // Fresh real result → fresh view: drop stale mock and real selections.
      setSelectedComponentId(null)
      setL2ComponentId(null)
      setSelectedRealId(null)
    } catch (err) {
      if (
        err instanceof Error &&
        err.message === INVALID_REPO_MESSAGE
      ) {
        setError(INVALID_REPO_MESSAGE)
      } else {
        setError(
          err instanceof Error
            ? err.message
            : 'Analyze request failed: unknown error',
        )
      }
    } finally {
      // Re-enable the button once the request settles, success or failure.
      setLoading(false)
    }
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

  // Stage B2: when a real analysis settled as done, the diagram renders its
  // `mermaid.source` directly. Otherwise `undefined` keeps the legacy
  // mock-shape diagram (initial page state), unchanged.
  const realDoneResult =
    analysisResult && analysisResult.status === 'done' ? analysisResult : null
  const realMermaidSource: string | null | undefined = realDoneResult
    ? (realDoneResult.mermaid?.source ?? null)
    : undefined
  const realFallback = realDoneResult
    ? toFallbackRows(realDoneResult.components, realDoneResult.edges)
    : undefined

  // Stage B3: list-driven drill-down over the real shape. `source_id` /
  // `target_id` resolve to `label.name` via a lookup built from
  // `components[]` — no refetch, no duplicated data.
  const realLabelMap = realDoneResult
    ? buildLabelMap(realDoneResult.components)
    : null
  const realLabelOf = (componentId: string) =>
    realLabelMap ? labelOfId(realLabelMap, componentId) : componentId

  // Stale real selection resolves to null → panel renders nothing.
  const realSelectedComponent =
    realDoneResult !== null && selectedRealId !== null
      ? (realDoneResult.components.find((c) => c.id === selectedRealId) ??
        null)
      : null

  return (
    <main className="app">
      <nav className="tab-bar" aria-label="Views">
        <button
          type="button"
          role="tab"
          aria-selected={view === 'analyze'}
          className={view === 'analyze' ? 'tab-button active' : 'tab-button'}
          onClick={() => setView('analyze')}
        >
          Analyze
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === 'compare'}
          className={view === 'compare' ? 'tab-button active' : 'tab-button'}
          onClick={() => setView('compare')}
        >
          Compare
        </button>
      </nav>

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      )}

      {view === 'analyze' ? (
        <>
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
            onAnalyze={() => void handleAnalyze()}
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
                {analyzeStatusMessage(analyzeElapsedSec)} ({analyzeElapsedSec}s)
              </span>
            )}
          </div>

          {analysisResult && (
            <section className="analyze-result" aria-label="Latest API result">
              <p>
                Analysis {analysisResult.status}:{' '}
                {analysisResult.components.length} components,{' '}
                {analysisResult.edges.length} edges{' '}
                <span className="file-path">
                  ({analysisResult.repo.owner}/{analysisResult.repo.name}@
                  {analysisResult.repo.commit_sha.slice(0, 7)})
                </span>
              </p>
            </section>
          )}

          {/* Stage B6: real mode shows the repo-identity header; the mock
              StatsBar's scanned/skipped numbers would be stale mock data
              here, so it stays on the mock path only — no stat shown twice. */}
          {realDoneResult ? (
            <RepoHeader repo={realDoneResult.repo} />
          ) : (
            <StatsBar
              stats={analysis.stats}
              showHeuristicBadge={showHeuristicBadge}
            />
          )}

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
                mermaidSource={realMermaidSource}
                realFallback={realFallback}
                onSelectComponent={(id) => {
                  // Legacy node-click path (mock data only) — inert on real
                  // diagrams; kept dormant per B3, clears the real selection
                  // so at most one panel is open.
                  setSelectedComponentId(id)
                  setSelectedRealId(null)
                }}
                fileName={
                  l2ComponentId === null
                    ? 'codeatlas-diagram.svg'
                    : `codeatlas-${l2ComponentId}.svg`
                }
              />
              {realDoneResult ? (
                <>
                  <ComponentList
                    components={realDoneResult.components}
                    selectedId={selectedRealId}
                    onSelect={(id) => {
                      setSelectedRealId(id)
                      setSelectedComponentId(null)
                    }}
                  />
                  <ConnectionsTable
                    edges={realDoneResult.edges}
                    labelOf={realLabelOf}
                  />
                  <UnresolvedImports
                    imports={realDoneResult.unresolved.imports}
                  />
                </>
              ) : (
                <ConnectionsTable
                  connections={displayAnalysis.connections}
                  labelOf={labelOf}
                />
              )}
            </div>
            {realDoneResult !== null && realSelectedComponent !== null ? (
              <SidePanel
                key={realSelectedComponent.id}
                component={realSelectedComponent}
                edges={realDoneResult.edges}
                parsedFiles={realDoneResult.parsed_files}
                labelOf={realLabelOf}
                onClose={() => setSelectedRealId(null)}
              />
            ) : (
              selectedComponent && (
                <SidePanel
                  key={selectedComponent.id}
                  component={selectedComponent}
                  connections={analysis.connections}
                  labelOf={labelOf}
                  onClose={() => setSelectedComponentId(null)}
                  onOpenDetailView={setL2ComponentId}
                />
              )
            )}
          </div>

          <section className="raw-data">
            <h2>Analysis data</h2>
            <pre>{JSON.stringify(analysis, null, 2)}</pre>
          </section>
        </>
      ) : (
        <>
          <h1 className="app-title">CodeAtlas</h1>
          <CompareView
            loading={loading}
            onLoadingChange={setLoading}
            onError={setError}
          />
        </>
      )}
    </main>
  )
}

export default App
