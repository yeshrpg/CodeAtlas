import { toNodeId } from './toMermaid'
import type { AnalysisComponent } from '../types'

/**
 * Matches Mermaid v12 flowchart node DOM ids, which are shaped as
 * "<renderId>-flowchart-<nodeId>-<index>" (verified against mermaid@12.0.0,
 * e.g. "codeatlas_r0_3-flowchart-api-0").
 *
 * Our node ids (see toNodeId) contain only [A-Za-z0-9_], so the middle
 * segment is unambiguous even when the render-id prefix contains dashes.
 */
const NODE_DOM_ID_RE = /-flowchart-([A-Za-z0-9_]+)-\d+$/

/**
 * Extract the Mermaid node id from a rendered `g.node` element's DOM id.
 * Returns null for non-matching ids (edges, labels, fallback content) —
 * callers should skip those silently.
 */
export function domIdToNodeId(domId: string | null | undefined): string | null {
  if (!domId) return null
  const match = NODE_DOM_ID_RE.exec(domId)
  return match ? match[1] : null
}

/**
 * Build a node-id -> component-id index from the analysis components,
 * using the same toNodeId mapping that generated the Mermaid source.
 */
export function buildNodeIndex(
  components: AnalysisComponent[] | null | undefined,
): Map<string, string> {
  const index = new Map<string, string>()
  if (!Array.isArray(components)) return index
  components.forEach((c, i) => {
    if (!c) return
    const nodeId = toNodeId(c.id, i)
    if (!index.has(nodeId)) {
      index.set(nodeId, c.id)
    } else {
      console.warn(
        `[CodeAtlas] duplicate Mermaid node id "${nodeId}" — keeping first component.`,
      )
    }
  })
  return index
}

/**
 * Attach click listeners to every rendered `g.node` under `root` that maps
 * back to a known component. Returns a cleanup function that removes all
 * attached listeners (call it before re-attaching on re-render).
 *
 * Set `quiet` when the index is known-inapplicable to the rendered SVG
 * (e.g. a real backend `mermaid.source` paired with the legacy mock
 * index): unmatched nodes are still skipped, but without the per-node
 * console warning, which would otherwise spam once per node.
 */
export function attachNodeClickListeners(
  root: ParentNode,
  index: Map<string, string>,
  onSelect: (componentId: string) => void,
  options?: { quiet?: boolean },
): () => void {
  const attached: Array<{ el: Element; handler: (e: Event) => void }> = []

  root.querySelectorAll('g.node').forEach((el) => {
    const nodeId = domIdToNodeId(el.getAttribute('id'))
    if (nodeId === null) return // not a node id we recognize — skip silently
    const componentId = index.get(nodeId)
    if (componentId === undefined) {
      if (!options?.quiet) {
        console.warn(
          `[CodeAtlas] rendered node "${nodeId}" has no matching component — skipping.`,
        )
      }
      return
    }
    const handler = () => onSelect(componentId)
    el.addEventListener('click', handler)
    el.classList.add('codeatlas-node')
    attached.push({ el, handler })
  })

  return () => {
    attached.forEach(({ el, handler }) => {
      el.removeEventListener('click', handler)
      el.classList.remove('codeatlas-node')
    })
  }
}
