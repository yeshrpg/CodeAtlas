import { toNodeId } from './toMermaid'
import { domIdToNodeId } from './nodeMapping'
import type { AnalysisHealth } from '../types'

/**
 * Health-flags overlay for the rendered Mermaid SVG (dead components +
 * cycle edges). Additive and best-effort by design:
 *
 * - When `health` is undefined/null/empty, this is a strict no-op — the
 *   caller should skip calling it at all (see `hasHealthIssues`), so the
 *   diagram renders pixel-identical to the no-health path.
 * - Every id match is best-effort using the same node-id conventions as
 *   the rest of the diagram code. Unmatchable ids are skipped silently.
 * - The whole body is wrapped in try/catch: a bug here must never take
 *   down the base diagram render.
 * - Only adds a CSS class + inline styles to matched elements; click
 *   listeners and all other behavior are untouched.
 */

const DEAD_NODE_CLASS = 'codeatlas-dead'
const CYCLE_EDGE_CLASS = 'codeatlas-cycle-edge'

const DEAD_FILL = '#e5e7eb'
const DEAD_STROKE = '#9ca3af'
const CYCLE_STROKE = '#dc2626'

/** True when there is at least one flaggable item to style/badge. */
export function hasHealthIssues(
  health: AnalysisHealth | null | undefined,
): boolean {
  if (!health || typeof health !== 'object') return false
  const cycles = (health as AnalysisHealth).cycles
  const dead = (health as AnalysisHealth).dead_components
  return (
    (Array.isArray(cycles) && cycles.length > 0) ||
    (Array.isArray(dead) && dead.length > 0)
  )
}

/**
 * Mirror of the backend's `_sanitize_id` (backend/app/services/mermaid.py):
 * the real diagram's node ids are produced by it, so a health component id
 * maps to its rendered node through this function.
 */
function backendSanitizeId(rawId: string): string {
  const sanitized = (rawId ?? '')
    .replace(/[^A-Za-z0-9_]/g, '_')
    .replace(/^_+|_+$/g, '')
  return sanitized || 'c'
}

/**
 * Candidate rendered node ids for one component id. Covers both the
 * backend sanitizer (real `mermaid.source` path) and the legacy frontend
 * `toNodeId` mapping (locally generated diagrams), so this works in
 * either mode.
 */
function candidateNodeIds(componentId: string): string[] {
  const out = new Set<string>()
  try {
    out.add(backendSanitizeId(componentId))
  } catch {
    /* skip */
  }
  try {
    out.add(toNodeId(componentId, 0))
  } catch {
    /* skip */
  }
  return [...out]
}

/** Directed sanitized pairs for one cycle, closed into a loop. */
function cyclePairs(cycle: unknown): Array<[string, string]> {
  const pairs: Array<[string, string]> = []
  try {
    if (!Array.isArray(cycle)) return pairs
    const ids = cycle.filter(
      (id): id is string => typeof id === 'string' && id.length > 0,
    )
    if (ids.length === 0) return pairs
    if (ids.length === 1) {
      // Self-loop: a single id cycling back to itself.
      for (const form of idForms(ids[0])) pairs.push([form, form])
      return pairs
    }
    for (let i = 0; i < ids.length; i++) {
      const from = ids[i]
      const to = ids[(i + 1) % ids.length]
      const fromForms = idForms(from)
      const toForms = idForms(to)
      // Pair every sanitizer form combination — a match on any form
      // counts, since either diagram path may have produced the node id.
      for (const a of fromForms) {
        for (const b of toForms) {
          pairs.push([a, b])
        }
      }
    }
  } catch {
    /* malformed cycle entry — skip silently */
  }
  return pairs
}

function idForms(componentId: string): string[] {
  const forms = new Set<string>()
  try {
    forms.add(backendSanitizeId(componentId))
  } catch {
    /* skip */
  }
  try {
    forms.add(toNodeId(componentId, 0))
  } catch {
    /* skip */
  }
  return [...forms]
}

/**
 * Parse directed edges from a Mermaid flowchart source in document order:
 * `src --> tgt` with an optional `|label|` segment. Returns [] when the
 * source is missing or unparsable — callers treat that as "no order info".
 */
function parseSourceEdges(source: string | null | undefined): Array<[string, string]> {
  const edges: Array<[string, string]> = []
  try {
    if (typeof source !== 'string' || source.length === 0) return edges
    const re = /^\s*([A-Za-z0-9_]+)\s*-->(?:\|[^|\n]*\|)?\s*([A-Za-z0-9_]+)/
    for (const line of source.split('\n')) {
      const m = re.exec(line)
      if (m) edges.push([m[1], m[2]])
    }
  } catch {
    /* unparsable source — order fallback unavailable, id matching still works */
  }
  return edges
}

type StyledEl = {
  el: Element
  className: string
  props: string[]
}

function setInline(el: Element, prop: string, value: string): void {
  ;(el as unknown as HTMLElement).style.setProperty(prop, value)
}

function clearInline(el: Element, prop: string): void {
  ;(el as unknown as HTMLElement).style.removeProperty(prop)
}

/**
 * Apply dead-node + cycle-edge styling to an already-rendered Mermaid SVG
 * under `root`. Returns a cleanup function that removes everything this
 * call added (the base render replaces innerHTML anyway; cleanup covers
 * the case where `health` changes without a re-render).
 *
 * Never throws: all failures degrade to "unstyled diagram".
 */
export function applyHealthStyling(
  root: ParentNode,
  health: AnalysisHealth | null | undefined,
  mermaidSource?: string | null,
): () => void {
  const noop = () => {}
  try {
    if (!root || !hasHealthIssues(health)) return noop
    const styled: StyledEl[] = []
    const track = (el: Element, className: string, props: string[]) => {
      styled.push({ el, className, props })
    }

    // --- Dead components: grey fill + dashed border on matched nodes ---
    try {
      const deadIds = new Set<string>()
      const dead = health?.dead_components
      if (Array.isArray(dead)) {
        for (const id of dead) {
          if (typeof id !== 'string') continue
          for (const form of candidateNodeIds(id)) deadIds.add(form)
        }
      }
      if (deadIds.size > 0) {
        root.querySelectorAll('g.node').forEach((node) => {
          try {
            const nodeId = domIdToNodeId(node.getAttribute('id'))
            if (nodeId === null || !deadIds.has(nodeId)) return
            node.classList.add(DEAD_NODE_CLASS)
            const shapeProps = ['fill', 'stroke', 'stroke-width', 'stroke-dasharray']
            // Style the shape element(s) inside the node, not the whole
            // group, so labels keep their normal text color.
            const shapes = node.querySelectorAll('rect, polygon, circle, ellipse')
            if (shapes.length > 0) {
              shapes.forEach((shape) => {
                setInline(shape, 'fill', DEAD_FILL)
                setInline(shape, 'stroke', DEAD_STROKE)
                setInline(shape, 'stroke-width', '1.5px')
                setInline(shape, 'stroke-dasharray', '6 3')
                track(shape, '', shapeProps)
              })
            } else {
              // No inner shape (unusual renderer output): fall back to
              // styling the group itself rather than skipping.
              setInline(node, 'fill', DEAD_FILL)
              setInline(node, 'stroke', DEAD_STROKE)
              setInline(node, 'stroke-dasharray', '6 3')
              track(node, '', ['fill', 'stroke', 'stroke-dasharray'])
            }
            track(node, DEAD_NODE_CLASS, [])
          } catch {
            /* one bad node — skip it, keep the rest */
          }
        })
      }
    } catch {
      /* dead-node pass failed — cycle pass below still runs */
    }

    // --- Cycles: red + thick stroke on edges between consecutive ids ---
    try {
      const pairSet = new Set<string>()
      const cycles = health?.cycles
      if (Array.isArray(cycles)) {
        for (const cycle of cycles) {
          for (const [a, b] of cyclePairs(cycle)) {
            pairSet.add(`${a}\0${b}`)
          }
        }
      }
      if (pairSet.size > 0) {
        const seen = new Set<Element>()
        const edgeEls: Element[] = []
        const collect = (selector: string) => {
          try {
            root.querySelectorAll(selector).forEach((el) => {
              if (!seen.has(el)) {
                seen.add(el)
                edgeEls.push(el)
              }
            })
          } catch {
            /* bad selector for this DOM — ignore */
          }
        }
        collect('.edgePaths path')
        collect('.edgePaths g')
        collect('path.flowchart-link')

        const matchesPair = (el: Element, a: string, b: string): boolean => {
          // Dagre (default layout): edge id embeds `L_<src>_<tgt>_<n>`.
          const id = el.getAttribute('id') ?? ''
          if (id.includes(`L_${a}_${b}_`)) return true
          // ELK layout: edges carry LS_<src> / LE_<tgt> classes.
          try {
            if (el.classList.contains(`LS_${a}`) && el.classList.contains(`LE_${b}`)) {
              return true
            }
          } catch {
            /* classList unavailable — ignore */
          }
          return false
        }

        const styleEdge = (el: Element) => {
          el.classList.add(CYCLE_EDGE_CLASS)
          setInline(el, 'stroke', CYCLE_STROKE)
          setInline(el, 'stroke-width', '3px')
          track(el, CYCLE_EDGE_CLASS, ['stroke', 'stroke-width'])
        }

        let matchedById = false
        for (const el of edgeEls) {
          try {
            let hit = false
            for (const key of pairSet) {
              const sep = key.indexOf('\0')
              const a = key.slice(0, sep)
              const b = key.slice(sep + 1)
              if (matchesPair(el, a, b)) {
                hit = true
                break
              }
            }
            if (hit) {
              styleEdge(el)
              matchedById = true
            }
          } catch {
            /* one bad edge — skip it */
          }
        }

        // Fallback: if id/class matching found nothing (unexpected edge
        // DOM shape), map source edges to rendered edges by document
        // order — Mermaid emits edges in source order.
        if (!matchedById) {
          try {
            const sourceEdges = parseSourceEdges(mermaidSource)
            if (sourceEdges.length > 0 && sourceEdges.length === edgeEls.length) {
              sourceEdges.forEach(([a, b], i) => {
                try {
                  if (pairSet.has(`${a}\0${b}`)) styleEdge(edgeEls[i])
                } catch {
                  /* skip */
                }
              })
            }
          } catch {
            /* order fallback failed — leave edges unstyled */
          }
        }
      }
    } catch {
      /* cycle pass failed — dead-node styling above still stands */
    }

    return () => {
      for (const { el, className, props } of styled) {
        try {
          if (className) el.classList.remove(className)
          for (const p of props) clearInline(el, p)
        } catch {
          /* cleanup best-effort */
        }
      }
    }
  } catch {
    return noop
  }
}
