"""
group.py — groups parsed files into 5-25 "components" for the diagram,
using folder structure only (no semantic/LLM grouping — locked spec: the
LLM never decides edges or structure).

Locked spec constraints honored here:
- Folder-based grouping only.
- Target component count: 5-25.
- Depth-search: try grouping by folder-path-prefix at depth 1 through 4,
  picking the shallowest depth that lands the component count in [5, 25].
- "other"-merge guard: if even at depth 4 there are more than 25 groups,
  merge the smallest groups into a synthetic "other" component until the
  count is <= 25 (never merges below 5 groups).
- flat-repo guard: if scan.py flagged the repo as flat (<=25 files, no
  meaningful nesting), skip depth-search entirely and make one component
  per file — folder depth-search is meaningless with no folders.
- Edges between components are derived only from resolve.py's resolved
  imports (cross-file references) — never guessed, never LLM-authored.
  Self-referencing edges (a file importing another file in its own
  component) are dropped since they wouldn't be visible in the diagram.

Public API:
    build_components(parsed_files, is_flat_repo) -> list[Component]
    build_edges(components, resolved_imports) -> list[ComponentEdge]
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Optional

try:
    from ..schema import Component, ComponentEdge
except ImportError:  # pragma: no cover - standalone/local testing fallback only
    from dataclasses import dataclass, field

    @dataclass
    class Component:
        id: str
        label: str
        files: list = field(default_factory=list)
        is_other: bool = False

    @dataclass
    class ComponentEdge:
        source: str
        target: str
        weight: int = 1


MIN_COMPONENTS = 5
MAX_COMPONENTS = 25
MAX_DEPTH = 4


def _group_key_at_depth(path: str, depth: int) -> str:
    """
    Folder-path-prefix key for a file at a given depth.
    Root-level files (no directory) always form their own "root" bucket,
    regardless of depth, since there's no folder to group them by.
    """
    parts = list(PurePosixPath(path).parts)
    dir_parts = parts[:-1]  # drop filename
    if not dir_parts:
        return "__root__"
    prefix = dir_parts[: min(depth, len(dir_parts))]
    return "/".join(prefix)


def _group_by_depth(parsed_files: list, depth: int) -> dict:
    groups: dict = {}
    for pf in parsed_files:
        key = _group_key_at_depth(pf.path, depth)
        groups.setdefault(key, []).append(pf.path)
    return groups


def _label_for_key(key: str) -> str:
    return "root" if key == "__root__" else key


def _merge_smallest_into_other(groups: dict) -> dict:
    """
    Repeatedly merge the smallest group into a synthetic "other" bucket
    until group count <= MAX_COMPONENTS, or until only MIN_COMPONENTS
    non-other groups remain (never merge below that floor).
    """
    groups = dict(groups)  # shallow copy, don't mutate caller's dict
    other_files: list = []
    other_key = "__other__"

    def effective_count() -> int:
        # +1 for the "other" bucket's own slot, but only once it's
        # actually going to exist (i.e. we've merged at least one group).
        return len(groups) + (1 if other_files else 0)

    while effective_count() > MAX_COMPONENTS:
        real_keys = [k for k in groups if k != other_key]
        if len(real_keys) <= MIN_COMPONENTS:
            break
        smallest_key = min(real_keys, key=lambda k: len(groups[k]))
        other_files.extend(groups.pop(smallest_key))

    if other_files:
        groups.setdefault(other_key, [])
        groups[other_key].extend(other_files)

    return groups


def build_components(parsed_files: list, is_flat_repo: bool) -> list:
    """
    Build the final component list for a repo's parsed files.
    """
    if not parsed_files:
        return []

    if is_flat_repo:
        # One component per file — folder depth-search doesn't apply.
        components = []
        for pf in parsed_files:
            file_id = pf.path
            components.append(
                Component(
                    id=file_id,
                    label=PurePosixPath(pf.path).name,
                    files=[pf.path],
                    is_other=False,
                )
            )
        return components

    chosen_groups: Optional[dict] = None
    for depth in range(1, MAX_DEPTH + 1):
        groups = _group_by_depth(parsed_files, depth)
        if MIN_COMPONENTS <= len(groups) <= MAX_COMPONENTS:
            chosen_groups = groups
            break
        # Keep the depth=MAX_DEPTH result as fallback if no depth in range
        # satisfies the window — it'll go through the merge guard below.
        chosen_groups = groups

    assert chosen_groups is not None

    if len(chosen_groups) > MAX_COMPONENTS:
        chosen_groups = _merge_smallest_into_other(chosen_groups)

    # If, after everything (very small repo with few folders), we still
    # have fewer than MIN_COMPONENTS groups, that's accepted as-is — the
    # spec's floor is a target for the search, not a hard requirement we
    # can manufacture components to satisfy (never invent structure that
    # isn't there).

    components = []
    for key, files in chosen_groups.items():
        is_other = key == "__other__"
        components.append(
            Component(
                id=key,
                label="other" if is_other else _label_for_key(key),
                files=sorted(files),
                is_other=is_other,
            )
        )
    return components


def _component_for_file(components: list, file_path: str) -> Optional[str]:
    for comp in components:
        if file_path in comp.files:
            return comp.id
    return None


def build_edges(components: list, resolved_imports: list) -> list:
    """
    Derive component-to-component edges purely from resolve.py's resolved
    imports. Multiple file-level imports between the same pair of
    components are collapsed into one edge with a weight = occurrence
    count. Self-loops (source and target file in the same component) are
    dropped.
    """
    file_to_component = {}
    for comp in components:
        for f in comp.files:
            file_to_component[f] = comp.id

    edge_weights: dict = {}
    for ri in resolved_imports:
        src_comp = file_to_component.get(ri.source_file)
        tgt_comp = file_to_component.get(ri.target_file)
        if src_comp is None or tgt_comp is None:
            continue  # shouldn't happen if components cover all parsed files
        if src_comp == tgt_comp:
            continue  # self-loop within a component — not shown
        key = (src_comp, tgt_comp)
        edge_weights[key] = edge_weights.get(key, 0) + 1

    return [
        ComponentEdge(source=src, target=tgt, weight=w)
        for (src, tgt), w in edge_weights.items()
    ]
