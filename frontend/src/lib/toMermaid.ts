import type {
  AnalysisComponent,
  AnalysisConnection,
} from '../types'

/**
 * Derive a stable Mermaid node id from a component id.
 * The mapping is deterministic (sanitize-only), so A4/A5 can map
 * rendered nodes back to components with this same function.
 * Exported for reuse by later stages.
 */
export function toNodeId(componentId: string, fallbackIndex = 0): string {
  const sanitized = (componentId ?? '')
    .trim()
    .replace(/[^A-Za-z0-9_]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
  if (!sanitized) return `node_${fallbackIndex}`
  // Mermaid node ids must not start with a digit.
  return /^[0-9]/.test(sanitized) ? `n_${sanitized}` : sanitized
}

/** Escape a label for use inside Mermaid's double-quoted node text. */
function escapeLabel(label: string): string {
  return (label ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, "'")
    .replace(/[#<>]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Pure function: analysis data -> Mermaid flowchart string.
 * Never throws: malformed/empty input yields a minimal valid diagram.
 */
export function toMermaid(
  components: AnalysisComponent[] | null | undefined,
  connections: AnalysisConnection[] | null | undefined,
): string {
  const comps = Array.isArray(components) ? components : []
  const conns = Array.isArray(connections) ? connections : []

  if (comps.length === 0) {
    return 'flowchart TD\n  empty["no data"]'
  }

  const lines = ['flowchart TD']
  const knownIds = new Set<string>()

  comps.forEach((c, i) => {
    const nodeId = toNodeId(c?.id, i)
    knownIds.add(nodeId)
    const label = escapeLabel(c?.label || c?.id || `component ${i}`) || 'component'
    lines.push(`  ${nodeId}["${label}"]`)
  })

  conns.forEach((conn) => {
    if (!conn) return
    const from = toNodeId(conn.from)
    const to = toNodeId(conn.to)
    // Skip edges referencing unknown nodes rather than emitting dangling ids.
    if (!knownIds.has(from) || !knownIds.has(to)) return
    const weight =
      typeof conn.weight === 'number' && Number.isFinite(conn.weight)
        ? `|${conn.weight}|`
        : ''
    lines.push(`  ${from} -->${weight} ${to}`)
  })

  return lines.join('\n')
}
