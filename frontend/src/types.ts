export interface AnalysisComponent {
  id: string
  label: string
  layer: string
  summary: string
  label_source: 'heuristic' | 'llm'
  files: string[]
}

export interface AnalysisConnection {
  from: string
  to: string
  weight: number
}

export interface AnalysisStats {
  files: number
  skipped: number
  edges: number
  unresolved_pct: number
  ms: number
}

export interface Analysis {
  components: AnalysisComponent[]
  connections: AnalysisConnection[]
  stats: AnalysisStats
}
