import type { AnalysisStats } from '../types'

interface StatsBarProps {
  stats: AnalysisStats
  showHeuristicBadge: boolean
}

function StatsBar({ stats, showHeuristicBadge }: StatsBarProps) {
  return (
    <section className="stats-bar" aria-label="Analysis stats">
      <span className="stat-chip">files: {stats.files}</span>
      <span className="stat-chip">skipped: {stats.skipped}</span>
      <span className="stat-chip">edges: {stats.edges}</span>
      <span className="stat-chip">unresolved: {stats.unresolved_pct}%</span>
      <span className="stat-chip">{stats.ms} ms</span>
      {showHeuristicBadge && (
        <span className="heuristic-badge">labels: heuristic</span>
      )}
    </section>
  )
}

export default StatsBar
