import type { ParsedFile } from '../types'

interface ParsedFileViewProps {
  /** Component file path that was clicked. */
  filePath: string
  /** Matching `parsed_files[]` entry, or null when absent. */
  parsed: ParsedFile | null
  onBack: (filePath: string) => void
  backLabel: string
}

/**
 * Stage B3: file-level drill-down for real analyses. Shows `symbols`,
 * `imports` and `docstring` when a matching `parsed_files[]` entry exists;
 * degrades to filename-only otherwise — never a crash.
 */
function ParsedFileView({ filePath, parsed, onBack, backLabel }: ParsedFileViewProps) {
  if (!parsed) {
    return (
      <div className="file-view">
        <button
          type="button"
          className="link-button"
          onClick={() => onBack(filePath)}
        >
          ← Back to {backLabel}
        </button>
        <h2 className="file-path">{filePath}</h2>
        <p className="empty-note">No parsed data for this file.</p>
      </div>
    )
  }

  const symbols = Array.isArray(parsed.symbols) ? parsed.symbols : []
  const imports = Array.isArray(parsed.imports) ? parsed.imports : []

  return (
    <div className="file-view">
      <button
        type="button"
        className="link-button"
        onClick={() => onBack(filePath)}
      >
        ← Back to {backLabel}
      </button>
      <h2 className="file-path">{parsed.path}</h2>
      <p className="component-meta">
        <span className="stat-chip">{parsed.language}</span>{' '}
        <span className="stat-chip">{parsed.line_count} lines</span>
      </p>
      {parsed.docstring && <p>{parsed.docstring}</p>}
      {parsed.parse_error && (
        <p className="validation-message">
          Parse error: {parsed.parse_error}
        </p>
      )}

      <h3>Symbols ({symbols.length})</h3>
      {symbols.length > 0 ? (
        <table className="fallback-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Kind</th>
              <th>Line</th>
            </tr>
          </thead>
          <tbody>
            {symbols.map((s, i) => (
              <tr key={`${s.name}:${s.line}:${i}`}>
                <td>
                  <code>{s.name}</code>
                </td>
                <td>{s.kind}</td>
                <td>{s.line}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-note">none</p>
      )}
      {symbols.some((s) => s.docstring ?? s.route_path) && (
        <>
          <h3>Symbol details</h3>
          <ul>
            {symbols
              .filter((s) => s.docstring ?? s.route_path)
              .map((s, i) => (
                <li key={`${s.name}:detail:${i}`}>
                  <code>{s.name}</code>
                  {s.route_path && (
                    <span>
                      {' '}
                      — {s.route_methods.join(', ')} {s.route_path}
                    </span>
                  )}
                  {s.docstring && <span>: {s.docstring}</span>}
                </li>
              ))}
          </ul>
        </>
      )}

      <h3>Imports ({imports.length})</h3>
      {imports.length > 0 ? (
        <table className="fallback-table">
          <thead>
            <tr>
              <th>Module</th>
              <th>Line</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {imports.map((imp, i) => (
              <tr key={`${imp.module}:${imp.line}:${i}`}>
                <td>
                  <code>{imp.module}</code>
                </td>
                <td>{imp.line}</td>
                <td>{imp.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-note">none</p>
      )}
    </div>
  )
}

export default ParsedFileView
