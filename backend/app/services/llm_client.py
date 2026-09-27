"""
llm_client.py — the single LLM touchpoint for an entire analysis.

Locked spec constraints honored here:
- ONE Gemini call per analysis, full stop. This module exposes exactly one
  public function (`enrich_components`) that makes at most one HTTP call.
- The LLM never decides edges and never writes Mermaid — its only job is
  to produce a short display label + one-sentence description per
  component, purely cosmetic enrichment on top of group.py's already-
  final structure.
- Model id comes from the `GEMINI_MODEL` env var (locked: confirmed exact
  string live in AI Studio, e.g. "gemini-3-flash-preview") — never
  hardcoded, so a model rename doesn't require a code change.
- Every network/LLM step has a deterministic fallback: if the API key is
  missing, the request fails, times out, or the response isn't valid
  JSON in the expected shape, we fall back to heuristic labels derived
  purely from folder names — the analysis must never hard-fail because
  Gemini was unavailable or rate-limited.
- Plain `def`, not `async def` (locked spec: API endpoints are sync def;
  this client follows the same convention so it composes directly with
  main.py's request handlers without an event loop).

Public API:
    enrich_components(components: list[Component]) -> list[ComponentEnrichment]
        Always returns exactly one enrichment per input component, in the
        same order. Never raises — falls back internally on any failure.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

try:
    from ..schema import Component
except ImportError:  # pragma: no cover - standalone/local testing fallback only
    from dataclasses import dataclass, field

    @dataclass
    class Component:
        id: str
        label: str
        files: list = field(default_factory=list)
        is_other: bool = False


class ComponentEnrichment:
    """Not necessarily a schema.py model — this is the enrichment payload
    merged onto a Component for the final AnalysisResult. Kept as a plain
    container here; main.py wiring (Y7) decides how it merges in."""

    __slots__ = ("component_id", "display_label", "description", "source")

    def __init__(self, component_id: str, display_label: str, description: str, source: str):
        self.component_id = component_id
        self.display_label = display_label
        self.description = description
        self.source = source  # "llm" or "fallback"

    def __repr__(self):
        return f"ComponentEnrichment({self.component_id!r}, {self.source})"


_GEMINI_TIMEOUT_SECONDS = 20
_MAX_FILES_LISTED_PER_COMPONENT = 8  # keep the prompt small — one call, don't blow context/RPM


def _fallback_label(comp: Component) -> str:
    if comp.is_other:
        return "Other / Misc"
    return comp.label.replace("_", " ").replace("/", " / ").title()


def _fallback_description(comp: Component) -> str:
    n = len(comp.files)
    noun = "file" if n == 1 else "files"
    if comp.is_other:
        return f"Miscellaneous grouping of {n} small {noun} not large enough to form their own component."
    return f"Code under '{comp.label}' containing {n} {noun}."


def _fallback_all(components: list) -> list:
    return [
        ComponentEnrichment(
            component_id=c.id,
            display_label=_fallback_label(c),
            description=_fallback_description(c),
            source="fallback",
        )
        for c in components
    ]


def _build_prompt(components: list) -> str:
    lines = [
        "You are labeling folders of a codebase diagram. For EACH component "
        "below, produce a short human-readable display label (2-4 words) and "
        "a single-sentence description of what that part of the codebase "
        "likely does, based only on its folder path and file names.",
        "",
        "Respond with ONLY a JSON array, no prose, no markdown fences. Each "
        "element must be an object with exactly these keys: "
        '"id", "display_label", "description". The "id" must exactly match '
        "the component id given below. Return exactly one object per "
        "component, in any order.",
        "",
        "Components:",
    ]
    for comp in components:
        sample_files = comp.files[:_MAX_FILES_LISTED_PER_COMPONENT]
        lines.append(
            f'- id: "{comp.id}" | folder: "{comp.label}" | '
            f"files: {sample_files}"
            + (" ... (truncated)" if len(comp.files) > _MAX_FILES_LISTED_PER_COMPONENT else "")
        )
    return "\n".join(lines)


def _extract_text_from_gemini_response(payload: dict) -> Optional[str]:
    try:
        candidates = payload.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in parts if "text" in p]
        return "".join(text_chunks) if text_chunks else None
    except (AttributeError, IndexError, TypeError):
        return None


def _parse_llm_json(raw_text: str, components: list) -> Optional[list]:
    """Returns a list of ComponentEnrichment (source='llm') only if the
    response is well-formed AND covers every component id exactly once;
    otherwise returns None so the caller falls back entirely (never mixes
    partial LLM results with fallback — keeps behavior predictable)."""
    text = raw_text.strip()
    # Defensive strip in case the model wraps in a markdown fence despite
    # instructions not to.
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
    seen_ids = set()
    enrichments = []
    for item in parsed:
        if not isinstance(item, dict):
            return None
        comp_id = item.get("id")
        label = item.get("display_label")
        desc = item.get("description")
        if not isinstance(comp_id, str) or not isinstance(label, str) or not isinstance(desc, str):
            return None
        if comp_id not in expected_ids or comp_id in seen_ids:
            return None
        seen_ids.add(comp_id)
        enrichments.append(
            ComponentEnrichment(component_id=comp_id, display_label=label.strip(),
                                 description=desc.strip(), source="llm")
        )

    if seen_ids != expected_ids:
        return None  # LLM dropped or duplicated a component — reject, fall back entirely

    # Re-order to match input component order for a predictable return shape.
    by_id = {e.component_id: e for e in enrichments}
    return [by_id[c.id] for c in components]


def enrich_components(components: list) -> list:
    """
    The ONE Gemini call for this analysis. Returns one ComponentEnrichment
    per input component, in input order, always — falling back to
    deterministic heuristic labels on any failure whatsoever.
    """
    if not components:
        return []

    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")
    if not api_key or not model:
        return _fallback_all(components)

    prompt = _build_prompt(components)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=_GEMINI_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return _fallback_all(components)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_all(components)

    text = _extract_text_from_gemini_response(payload)
    if text is None:
        return _fallback_all(components)

    result = _parse_llm_json(text, components)
    if result is None:
        return _fallback_all(components)

    return result
