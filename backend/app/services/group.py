"""
group.py — groups parsed files into 5-25 "components" for the diagram,
using folder structure only. Also derives ComponentEdge objects from
already-resolved imports on the final schema.ParsedFile objects (resolve.py
already stamped resolved_path/status onto each ImportRef, so no separate
"resolved imports" structure is needed here).

Locked spec constraints honored here:
- Folder-based grouping only. Target component count: 5-25.
- Depth-search: try grouping by folder-path-prefix at depth 1-4, picking
  the shallowest depth landing the count in [5, 25].
- "other"-merge guard: if even at depth 4 there are more than 25 groups,
  merge the smallest into a synthetic "other" component (is_other_merge)
  until count <= 25 (never merges below 5 real groups).
- flat-repo guard: if scan.py flagged is_flat_repo, skip depth-search and
  make one component per file.
- schema.Component.label is a required ComponentLabel (name, summary,
  source). group.py assigns a heuristic label at construction time
  (LabelSource.heuristic) — llm_client.py (Y6) may later replace it with
  an LLM-sourced label via model_copy; group.py never leaves label unset.
- Edges only come from ImportRef entries with status == resolved — never
  guessed, never LLM-authored. Self-references (source and target file in
  the same component) are dropped.

Public API:
    build_components(parsed_files: list[ParsedFile], is_flat_repo: bool) -> list[Component]
    build_edges(components: list[Component], parsed_files: list[ParsedFile]) -> list[ComponentEdge]
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Optional

from ..schema import Component, ComponentEdge, ComponentLabel, ImportResolutionStatus, LabelSource

MIN_COMPONENTS = 5
MAX_COMPONENTS = 25
MAX_DEPTH = 4

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_]")


def _slugify(key: str) -> str:
    return _SLUG_RE.sub("_", key).strip("_") or "root"


def _unique_id(base: str, used: set) -> str:
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}_{n}"
        n += 1
    used.add(candidate)
    return candidate


def _group_key_at_depth(path: str, depth: int) -> str:
    parts = list(PurePosixPath(path).parts)
    dir_parts = parts[:-1]
    if not dir_parts:
        return ""  # repo-root files
    return "/".join(dir_parts[: min(depth, len(dir_parts))])


def _group_by_depth(parsed_files: list, depth: int) -> dict:
    groups: dict = {}
    for pf in parsed_files:
        key = _group_key_at_depth(pf.path, depth)
        groups.setdefault(key, []).append(pf.path)
    return groups


def _merge_smallest_into_other(groups: dict) -> dict:
    groups = dict(groups)
    other_files: list = []
    other_key = "__other__"

    def effective_count() -> int:
        return len(groups) + (1 if other_files else 0)

    while effective_count() > MAX_COMPONENTS:
        real_keys = [k for k in groups if k != other_key]
        if len(real_keys) <= MIN_COMPONENTS:
            break
        smallest_key = min(real_keys, key=lambda k: len(groups[k]))
        other_files.extend(groups.pop(smallest_key))

    if other_files:
        groups[other_key] = groups.get(other_key, []) + other_files

    return groups


def _heuristic_label(folder_key: str, file_count: int, is_other: bool) -> ComponentLabel:
    if is_other:
        name = "Other / Misc"
        summary = f"Miscellaneous grouping of {file_count} small file(s) not large enough to form their own component."
    elif folder_key in ("", "__root__"):
        name = "Root"
        summary = f"Top-level repo files ({file_count} file(s))."
    else:
        name = folder_key.replace("/", " / ").replace("_", " ").title()
        noun = "file" if file_count == 1 else "files"
        summary = f"Code under '{folder_key}' containing {file_count} {noun}."
    return ComponentLabel(name=name, summary=summary, source=LabelSource.heuristic)


def build_components(parsed_files: list, is_flat_repo: bool) -> list:
    if not parsed_files:
        return []

    used_ids: set = set()

    if is_flat_repo:
        components = []
        for pf in parsed_files:
            comp_id = _unique_id(_slugify(PurePosixPath(pf.path).stem), used_ids)
            components.append(Component(
                id=comp_id,
                folder_path="",
                files=[pf.path],
                label=_heuristic_label(PurePosixPath(pf.path).name, 1, is_other=False),
                is_other_merge=False,
            ))
        return components

    chosen_groups: Optional[dict] = None
    for depth in range(1, MAX_DEPTH + 1):
        groups = _group_by_depth(parsed_files, depth)
        chosen_groups = groups
        if MIN_COMPONENTS <= len(groups) <= MAX_COMPONENTS:
            break

    assert chosen_groups is not None
    if len(chosen_groups) > MAX_COMPONENTS:
        chosen_groups = _merge_smallest_into_other(chosen_groups)

    components = []
    for key, files in chosen_groups.items():
        is_other = key == "__other__"
        folder_path = "" if key in ("", "__other__") else key
        comp_id = _unique_id(_slugify(key) if key not in ("", "__other__") else ("root" if key == "" else "other"), used_ids)
        components.append(Component(
            id=comp_id,
            folder_path=folder_path,
            files=sorted(files),
            label=_heuristic_label(key, len(files), is_other=is_other),
            is_other_merge=is_other,
        ))
    return components


def build_edges(components: list, parsed_files: list) -> list:
    """
    Derive component-to-component edges purely from ImportRef entries with
    status == resolved. Multiple file-level imports between the same pair
    of components collapse into one edge with import_count = occurrence
    count and evidence = ["file:line", ...]. Self-loops are dropped.
    """
    file_to_component = {}
    for comp in components:
        for f in comp.files:
            file_to_component[f] = comp.id

    edge_data: dict = {}  # (src_id, tgt_id) -> {"count": int, "evidence": list[str]}

    for pf in parsed_files:
        src_comp = file_to_component.get(pf.path)
        if src_comp is None:
            continue
        for imp in pf.imports:
            if imp.status != ImportResolutionStatus.resolved or not imp.resolved_path:
                continue
            tgt_comp = file_to_component.get(imp.resolved_path)
            if tgt_comp is None or tgt_comp == src_comp:
                continue
            key = (src_comp, tgt_comp)
            entry = edge_data.setdefault(key, {"count": 0, "evidence": []})
            entry["count"] += 1
            entry["evidence"].append(f"{pf.path}:{imp.line}")

    return [
        ComponentEdge(
            source_id=src, target_id=tgt,
            import_count=data["count"], evidence=data["evidence"],
        )
        for (src, tgt), data in edge_data.items()
    ]
