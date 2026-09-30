import type { AnalysisHealth } from '../types'
import { hasHealthIssues } from '../lib/applyHealthStyling'

interface HealthIssuesPanelProps {
  /** Backend `health` field — null/absent/empty renders nothing. */
  health?: AnalysisHealth | null
}

/** Best-effort string list: non-array input yields [], non-strings dropped. */
function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter(
    (v): v is string => typeof v === 'string' && v.length > 0,
  )
}

/** Best-effort cycle list: malformed entries yield [] and are dropped. */
function asCycleList(value: unknown): string[][] {
  if (!Array.isArray(value)) return []
  return value
    .map((cycle) => (Array.isArray(cycle) ? asStringList(cycle) : []))
    .filter((cycle) => cycle.length > 0)
}

/**
 * Warning panel listing circular dependencies and dead components from the
 * backend `health` report. Renders nothing (null) when health is absent,
 * null, or issue-free — so the no-health diagram stays pixel-identical.
 * Never throws: malformed payloads degrade to fewer (or zero) rows.
 */
export function HealthIssuesPanel({ health }: HealthIssuesPanelProps) {
  if (!hasHealthIssues(health)) return null
  const cycles = asCycleList(health?.cycles)
  const deadComponents = asStringList(health?.dead_components)
  if (cycles.length === 0 && deadComponents.length === 0) return null
  const summary = typeof health?.summary === 'string' ? health.summary : ''

  return (
    <section className="health-panel" aria-label="Architectural health issues">
      <div className="health-panel-header">
        <span className="health-panel-icon" aria-hidden="true">
          ⚠️
        </span>
        <h3 className="health-panel-title">Architectural Issues Detected</h3>
      </div>

      {summary.length > 0 ? (
        <p className="health-panel-summary">{summary}</p>
      ) : null}

      {cycles.length > 0 ? (
        <div className="health-panel-group">
          <h4 className="health-panel-subtitle">Circular Dependencies</h4>
          <ul className="health-cycle-list">
            {cycles.map((cycle, i) => (
              <li key={`cycle-${i}`} className="health-cycle-item">
                {cycle.join(' → ')}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {deadComponents.length > 0 ? (
        <div className="health-panel-group">
          <h4 className="health-panel-subtitle">
            Unused / Disconnected Components
          </h4>
          <ul className="health-dead-list">
            {deadComponents.map((id, i) => (
              <li key={`${id}-${i}`} className="health-dead-item">
                {id}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

export default HealthIssuesPanel
