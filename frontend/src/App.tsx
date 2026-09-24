import { useState } from 'react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import DemoDropdown from './components/DemoDropdown'
import ErrorBanner from './components/ErrorBanner'
import DiagramView from './components/DiagramView'
import mockData from './mock/analysis.json'
import type { Analysis } from './types'
import './App.css'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [ref, setRef] = useState('')
  const [analysis, setAnalysis] = useState<Analysis>(mockData as Analysis)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  )

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
      setAnalysis(mockData as Analysis)
      setLoading(false)
    }, 500)
  }

  const showHeuristicBadge = analysis.components.some(
    (c) => c.label_source === 'heuristic',
  )

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
            setAnalysis(data)
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

      <DiagramView analysis={analysis} />

      <section className="raw-data">
        <h2>Analysis data</h2>
        <pre>{JSON.stringify(analysis, null, 2)}</pre>
      </section>
    </main>
  )
}

export default App
