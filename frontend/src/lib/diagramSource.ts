import type { Component, ComponentEdge } from '../types'

/**
 * Stage B2: which Mermaid input feeds `mermaid.render()`.
 * - `legacy`: no real result yet — generate locally via toMermaid from the
 *   mock shape (Compare tab + pre-analyze default). Unchanged A3 behavior.
 * - `direct`: real `AnalysisResult` with status "done" — render
 *   `mermaid.source` verbatim, no local conversion step.
 * - `empty`: backend returned `mermaid: null` — empty state, never a crash.
 */
export type DiagramSource =
  | { kind: 'legacy' }
  | { kind: 'direct'; code: string }
  | { kind: 'empty' }

export function resolveDiagramSource(
  mermaidSource: string | null | undefined,
): DiagramSource {
  if (mermaidSource === undefined) return { kind: 'legacy' }
  if (mermaidSource === null) return { kind: 'empty' }
  return { kind: 'direct', code: mermaidSource }
}

export interface FallbackComponentRow {
  id: string
  label: string
  layer: string
}

export interface FallbackConnectionRow {
  from: string
  to: string
  weight: number
}

export interface FallbackTables {
  components: FallbackComponentRow[]
  connections: FallbackConnectionRow[]
}

/**
 * Map the real backend shape onto the rows the fallback table renders, so a
 * failed direct render still shows real data (never stale mock data).
 * Never throws: non-array input yields empty tables.
 */
export function toFallbackRows(
  components: Component[] | null | undefined,
  edges: ComponentEdge[] | null | undefined,
): FallbackTables {
  const comps = Array.isArray(components) ? components : []
  const edgs = Array.isArray(edges) ? edges : []
  return {
    components: comps.map((c) => ({
      id: c?.id ?? '',
      label: c?.label?.name ?? c?.id ?? '',
      layer: c?.folder_path ?? '',
    })),
    connections: edgs.map((e) => ({
      from: e?.source_id ?? '',
      to: e?.target_id ?? '',
      weight: e?.import_count ?? 0,
    })),
  }
}
