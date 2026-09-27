"""
mermaid.py — renders a component graph (from group.py) into Mermaid
flowchart syntax. Purely deterministic templating — the LLM never writes
Mermaid and never decides edges; this module only consumes already-final
Component/ComponentEdge data.

Mermaid node-id handling:
- schema.Component.id is already a slug (group.py guarantees uniqueness),
  but we still defensively re-sanitize here in case any id ever contains
  a character Mermaid can't use in a bare node id.
- Node label text comes from Component.label.name (not folder_path) plus
  a file count, since label.name is the human-readable one.
- is_other_merge components get a distinct CSS class so they read as a
  catch-all rather than a real folder.
- Edge weight (import_count) is shown as an edge label only when > 1.

Public API:
    render_mermaid(components: list[Component], edges: list[ComponentEdge]) -> MermaidOutput
"""

from __future__ import annotations

import re

from ..schema import MermaidOutput

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_]")


def _sanitize_id(raw_id: str) -> str:
    return _SAFE_ID_RE.sub("_", raw_id).strip("_") or "c"


def _escape_label(label: str) -> str:
    escaped = label.replace("\\", "\\\\").replace('"', "&quot;")
    return escaped.replace("[", "&#91;").replace("]", "&#93;")


def render_mermaid(components: list, edges: list) -> MermaidOutput:
    if not components:
        return MermaidOutput(diagram_type="graph TD", source="graph TD\n")

    id_map = {}
    lines = ["graph TD"]

    for comp in components:
        node_id = _sanitize_id(comp.id)
        id_map[comp.id] = node_id
        file_count = len(comp.files)
        display_label = f"{_escape_label(comp.label.name)} ({file_count} file{'s' if file_count != 1 else ''})"
        lines.append(f'    {node_id}["{display_label}"]')
        if comp.is_other_merge:
            lines.append(f"    class {node_id} otherNode")

    lines.append("")

    for edge in edges:
        src_id = id_map.get(edge.source_id)
        tgt_id = id_map.get(edge.target_id)
        if src_id is None or tgt_id is None:
            continue
        if edge.import_count > 1:
            lines.append(f"    {src_id} -->|{edge.import_count}| {tgt_id}")
        else:
            lines.append(f"    {src_id} --> {tgt_id}")

    lines.append("")
    lines.append("    classDef otherNode fill:#eee,stroke:#999,stroke-dasharray: 4 3")

    diagram = "\n".join(lines) + "\n"
    return MermaidOutput(diagram_type="graph TD", source=diagram)
