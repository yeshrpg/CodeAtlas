export interface FileImport {
  name: string
  line: number
  from?: string
}

export interface FileDetail {
  symbols: string[]
  imports: FileImport[]
  importers: string[]
}

export interface AnalysisComponent {
  id: string
  label: string
  layer: string
  summary: string
  label_source: 'heuristic' | 'llm'
  files: string[]
  file_details?: Record<string, FileDetail>
}

export interface EvidenceLine {
  file: string
  line: number
  text: string
}

export interface AnalysisConnection {
  from: string
  to: string
  weight: number
  evidence?: EvidenceLine[]
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

export interface CompareEndpoint {
  repo_url: string
  ref?: string
}

export interface CompareResponse {
  analysis: Analysis
  added_components: string[]
  removed_components: string[]
  added_connections: AnalysisConnection[]
  removed_connections: AnalysisConnection[]
  reading_order?: string[]
}
