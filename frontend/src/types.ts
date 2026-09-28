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

// ---------------------------------------------------------------------------
// Real backend contract (Stage B1). Source of truth: backend schema.
// Kept alongside the legacy mock types above — CompareView (P1) still
// depends on those, so they must not be removed in this stage.
// ---------------------------------------------------------------------------

export type AnalysisResult = {
  analysis_id: string
  status: 'pending' | 'running' | 'done' | 'failed'
  error: string | null
  created_at: string
  completed_at: string | null
  repo: {
    owner: string
    name: string
    default_branch: string
    commit_sha: string
    is_public: boolean
    total_files_scanned: number
    total_files_skipped: number
    total_size_bytes: number
    is_flat_repo: boolean
  }
  components: Component[]
  edges: ComponentEdge[]
  unresolved: { imports: ImportRef[] }
  parsed_files: ParsedFile[]
  mermaid: { diagram_type: 'graph TD' | 'graph LR'; source: string } | null
  llm_model: string | null
  llm_call_count: 0 | 1
}

export type Component = {
  id: string
  folder_path: string
  files: string[]
  label: { name: string; summary: string; source: 'llm' | 'heuristic' }
  is_other_merge: boolean
}

export type ComponentEdge = {
  source_id: string
  target_id: string
  import_count: number
  evidence: string[]
}

export type ImportRef = {
  raw: string
  module: string
  line: number
  status: 'resolved' | 'unresolved' | 'external'
  resolved_path: string | null
}

export type ParsedFile = {
  path: string
  language: 'python' | 'javascript' | 'typescript' | 'other'
  line_count: number
  docstring: string | null
  imports: ImportRef[]
  symbols: {
    name: string
    kind: 'function' | 'class' | 'route' | 'variable'
    line: number
    docstring: string | null
    route_path: string | null
    route_methods: string[]
  }[]
  parse_error: string | null
}
