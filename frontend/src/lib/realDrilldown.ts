import type { Component, ComponentEdge, ParsedFile } from '../types'

/**
 * Stage B3: pure helpers for the list-driven drill-down over the real
 * backend shape. No DOM, no React — unit-tested headlessly. Field names
 * match the backend schema exactly; no renaming/aliasing.
 */

/** Resolve `source_id`/`target_id` to a component's `label.name`. */
export function buildLabelMap(components: Component[] | null | undefined): Map<string, string> {
  const map = new Map<string, string>()
  if (!Array.isArray(components)) return map
  for (const c of components) {
    if (c && typeof c.id === 'string') {
      map.set(c.id, c.label?.name ?? c.id)
    }
  }
  return map
}

/** Unknown ids fall back to the raw id — never blank, never a crash. */
export function labelOfId(labelMap: Map<string, string>, componentId: string): string {
  return labelMap.get(componentId) ?? componentId
}

/** Edges pointing at this component (`target_id === component.id`). */
export function incomingEdges(
  edges: ComponentEdge[] | null | undefined,
  componentId: string,
): ComponentEdge[] {
  if (!Array.isArray(edges)) return []
  return edges.filter((e) => e && e.target_id === componentId)
}

/** Edges leaving this component (`source_id === component.id`). */
export function outgoingEdges(
  edges: ComponentEdge[] | null | undefined,
  componentId: string,
): ComponentEdge[] {
  if (!Array.isArray(edges)) return []
  return edges.filter((e) => e && e.source_id === componentId)
}

/**
 * File-level drill-down: match a component file against `parsed_files[]`
 * by exact path. Returns null when absent — callers degrade to filename-only.
 */
export function findParsedFile(
  parsedFiles: ParsedFile[] | null | undefined,
  path: string,
): ParsedFile | null {
  if (!Array.isArray(parsedFiles)) return null
  return parsedFiles.find((p) => p && p.path === path) ?? null
}
