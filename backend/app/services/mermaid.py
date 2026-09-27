"""
mermaid.py — renders a component graph (from group.py) into Mermaid
flowchart syntax. Purely deterministic templating.

Locked spec constraint honored here:
- The LLM never decides edges and never writes Mermaid. This module is
  the only thing that produces Mermaid syntax, and it does so from
  already-computed Component/ComponentEdge data only.

Mermaid node-id rules handled here:
- Component.id values come straight from folder paths (e.g. "api/a",
  "__root__", "__other__") and contain characters Mermaid node IDs can't
  safely contain (/, ., spaces, leading underscores in some renderers).
  Every component gets a sanitized, guaranteed-unique node id; the
  original folder path is kept as the *label*, not the id.
- Labels are wrapped in quotes and have internal quotes/brackets escaped
  so a folder or file name can never break the diagram syntax.
- The synthetic "other" component (is_other=True) gets a distinct CSS
  class (`otherNode`) so it reads visually as a catch-all, not a real
  folder.
- Edge weight (from group.py's collapsed import counts) is rendered as
  an edge label only when weight > 1, to avoid clutter on the common
  single-import case.

Public API:
    render_mermaid(components: list[Component], edges: list[ComponentEdge]) -> MermaidOutput
"""

from __future__ import annotations

import re

try:
    from ..schema import MermaidOutput
except ImportError:  # pragma: no cover - standalone/local testing fallback only
    from dataclasses import dataclass

    @dataclass
    class MermaidOutput:
        diagram: str
        node_count: int
        edge_count: int


_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_]")


def _sanitize_id(raw_id: str, index: int) -> str:
    """
    Produce a Mermaid-safe node id. Not required to be human-readable —
    just stable and collision-free within one render call. We prefix
    with 'n' + index to guarantee uniqueness even if two component ids
    sanitize to the same string (e.g. "api/a" and "api.a").
    """
    cleaned = _SAFE_ID_RE.sub("_", raw_id).strip("_") or "c"
    return f"n{index}_{cleaned}"[:64]  # keep ids reasonably short


def _escape_label(label: str) -> str:
    """Escape characters that would break a quoted Mermaid label."""
    escaped = label.replace("\\", "\\\\").replace('"', "&quot;")
    escaped = escaped.replace("[", "&#91;").replace("]", "&#93;")
    return escaped


def render_mermaid(components: list, edges: list) -> "MermaidOutput":
    if not components:
        return MermaidOutput(diagram="flowchart TD\n", node_count=0, edge_count=0)

    id_map = {}
    lines = ["flowchart TD"]

    for i, comp in enumerate(components):
        node_id = _sanitize_id(comp.id, i)
        id_map[comp.id] = node_id
        label = _escape_label(comp.label)
        file_count = len(comp.files)
        display_label = f"{label} ({file_count} file{'s' if file_count != 1 else ''})"
        lines.append(f'    {node_id}["{display_label}"]')
        if getattr(comp, "is_other", False):
            lines.append(f"    class {node_id} otherNode")

    lines.append("")  # blank line between node defs and edges for readability

    edge_count = 0
    for edge in edges:
        src_id = id_map.get(edge.source)
        tgt_id = id_map.get(edge.target)
        if src_id is None or tgt_id is None:
            # Edge referencing a component not in this render's component
            # list — skip rather than emit a dangling/invalid reference.
            continue
        weight = getattr(edge, "weight", 1)
        if weight > 1:
            lines.append(f"    {src_id} -->|{weight}| {tgt_id}")
        else:
            lines.append(f"    {src_id} --> {tgt_id}")
        edge_count += 1

    lines.append("")
    lines.append("    classDef otherNode fill:#eee,stroke:#999,stroke-dasharray: 4 3")

    diagram = "\n".join(lines) + "\n"
    return MermaidOutput(diagram=diagram, node_count=len(components), edge_count=edge_count)
