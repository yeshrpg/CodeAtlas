"""
llm_client.py — the single LLM touchpoint for an entire analysis.

Locked spec constraints honored here:
- ONE Gemini call per analysis. This module exposes exactly one public
  function (`enrich_components`) that makes at most one HTTP call.
- The LLM never decides edges and never writes Mermaid — its only job is
  to replace each component's heuristic ComponentLabel (already set by
  group.py) with a better one, where possible.
- Model id comes from the `GEMINI_MODEL` env var, never hardcoded.
- Deterministic fallback: since group.py already gave every Component a
  heuristic label before this runs, "falling back" here means simply
  returning the input components unchanged — there's no separate fallback
  label logic to duplicate.
- Plain `def`, not `async def`.

Public API:
    enrich_components(components: list[Component]) -> list[Component]
        Always returns exactly one Component per input, same order, same
        id/folder_path/files/is_other_merge. Only `label` may differ
        (replaced with an LLM-sourced ComponentLabel on full success).
        Never raises.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from ..schema import Component, ComponentLabel, LabelSource

_GEMINI_TIMEOUT_SECONDS = 20
_MAX_FILES_LISTED_PER_COMPONENT = 8


def _build_prompt(components: list) -> str:
    lines = [
        "You are labeling folders of a codebase diagram. For EACH component "
        "below, produce a short human-readable name (2-4 words) and a "
        "single-sentence summary of what that part of the codebase likely "
        "does, based only on its folder path and file names.",
        "",
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each "
        'element must be an object with exactly these keys: "id", "name", '
        '"summary". The "id" must exactly match the component id given '
        "below. Return exactly one object per component.",
        "",
        "Components:",
    ]
    for comp in components:
        sample_files = comp.files[:_MAX_FILES_LISTED_PER_COMPONENT]
        truncated = " ... (truncated)" if len(comp.files) > _MAX_FILES_LISTED_PER_COMPONENT else ""
        lines.append(f'- id: "{comp.id}" | folder: "{comp.folder_path}" | files: {sample_files}{truncated}')
    return "\n".join(lines)


def _extract_text(payload: dict) -> Optional[str]:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        chunks = [p.get("text", "") for p in parts if "text" in p]
        return "".join(chunks) if chunks else None
    except (KeyError, IndexError, TypeError):
        return None


def _parse_llm_json(raw_text: str, components: list) -> Optional[dict]:
    """Returns {component_id: (name, summary)} only if the response is
    well-formed AND covers every component id exactly once; otherwise None
    (full fallback — never mixes partial LLM results with heuristics)."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None

    expected_ids = {c.id for c in components}
    seen = {}
    for item in parsed:
        if not isinstance(item, dict):
            return None
        cid, name, summary = item.get("id"), item.get("name"), item.get("summary")
        if not all(isinstance(x, str) for x in (cid, name, summary)):
            return None
        if cid not in expected_ids or cid in seen:
            return None
        seen[cid] = (name.strip(), summary.strip())

    if set(seen) != expected_ids:
        return None
    return seen


def enrich_components(components: list) -> list:
    """The ONE Gemini call for this analysis."""
    if not components:
        return []

    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")
    if not api_key or not model:
        return components  # heuristic labels from group.py stand as-is

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": _build_prompt(components)}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=_GEMINI_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return components

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return components

    text = _extract_text(payload)
    if text is None:
        return components

    labels = _parse_llm_json(text, components)
    if labels is None:
        return components

    enriched = []
    for comp in components:
        name, summary = labels[comp.id]
        new_label = ComponentLabel(name=name, summary=summary, source=LabelSource.llm)
        enriched.append(comp.model_copy(update={"label": new_label}))
    return enriched
