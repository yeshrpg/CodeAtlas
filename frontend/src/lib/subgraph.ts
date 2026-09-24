import type { Analysis } from '../types'

/**
 * Pure function: filter the full L1 analysis down to an L2 view for one
 * component — the component itself plus its direct neighbors (both
 * directions), and only connections between components in that subset.
 * Unknown ids yield an empty-component analysis (toMermaid renders a
 * "no data" node for that) — never throws.
 */
export function toL2Analysis(
  analysis: Analysis,
  componentId: string,
): Analysis {
  const components = Array.isArray(analysis?.components)
    ? analysis.components
    : []
  const connections = Array.isArray(analysis?.connections)
    ? analysis.connections
    : []

  const ids = new Set<string>([componentId])
  connections.forEach((c) => {
    if (!c) return
    if (c.from === componentId) ids.add(c.to)
    if (c.to === componentId) ids.add(c.from)
  })

  return {
    ...analysis,
    components: components.filter((c) => c && ids.has(c.id)),
    connections: connections.filter(
      (c) => c && ids.has(c.from) && ids.has(c.to),
    ),
  }
}
