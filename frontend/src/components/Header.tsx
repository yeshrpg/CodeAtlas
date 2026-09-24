interface HeaderProps {
  repoUrl: string
  ref: string
  loading: boolean
  validationMessage: string | null
  onRepoUrlChange: (value: string) => void
  onRefChange: (value: string) => void
  onAnalyze: () => void
}

function Header({
  repoUrl,
  ref,
  loading,
  validationMessage,
  onRepoUrlChange,
  onRefChange,
  onAnalyze,
}: HeaderProps) {
  return (
    <header className="app-header">
      <h1 className="app-title">CodeAtlas</h1>
      <div className="header-controls">
        <input
          type="text"
          className="text-input"
          placeholder="Repository URL (e.g. https://github.com/org/repo)"
          value={repoUrl}
          onChange={(e) => onRepoUrlChange(e.target.value)}
          disabled={loading}
        />
        <input
          type="text"
          className="text-input ref-input"
          placeholder="Ref / branch (optional)"
          value={ref}
          onChange={(e) => onRefChange(e.target.value)}
          disabled={loading}
        />
        <button
          type="button"
          className="analyze-button"
          onClick={onAnalyze}
          disabled={loading}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      {validationMessage && (
        <p className="validation-message" role="alert">
          {validationMessage}
        </p>
      )}
    </header>
  )
}

export default Header
