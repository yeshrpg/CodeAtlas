"""
llm_client.py — the single LLM touchpoint for an entire analysis.

Locked spec constraints honored here:
- ONE successful Gemini call per analysis. `enrich_components` is the only
  public function. It may RETRY transient failures (429/5xx/timeouts) and may
  fall back to GEMINI_FALLBACK_MODEL, but it stops at the first well-formed
  response, so llm_call_count in the pipeline stays 0 or 1.
- The LLM never decides edges and never writes Mermaid — its only job is
  to replace each component's heuristic ComponentLabel (set by group.py).
- Model ids come from env vars (GEMINI_MODEL, optional GEMINI_FALLBACK_MODEL).
- Deterministic fallback: on any failure, return the input components
  unchanged (group.py already gave every Component a heuristic label).
- Plain `def`, not `async def`. Never raises.

Public API:
    enrich_components(components: list[Component]) -> list[Component]
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from ..schema import Component, ComponentLabel, LabelSource

logger = logging.getLogger("codeatlas.llm")

_PER_ATTEMPT_TIMEOUT_SECONDS = 15
_TOTAL_DEADLINE_SECONDS = 40  # whole enrichment budget, all attempts combined
_ATTEMPTS_PER_MODEL = 2
_BACKOFF_SECONDS = (1.5, 3.0)
_RETRYABLE_HTTP = {429, 500, 502, 503, 504}
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


def _call_once(model: str, api_key: str, body: bytes, timeout: float):
    """One HTTP attempt. Returns (payload_dict | None, retryable: bool, note: str).
    The API key goes in a header (not the URL) so it can never leak into
    exception messages or logs."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return None, e.code in _RETRYABLE_HTTP, f"http {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, True, f"network {type(e).__name__}"
    try:
        return json.loads(raw), False, "ok"
    except json.JSONDecodeError:
        return None, True, "bad json envelope"


def enrich_components(components: list) -> list:
    """The ONE successful Gemini call for this analysis (with retries)."""
    if not components:
        return []

    api_key = os.environ.get("GEMINI_API_KEY")
    primary = os.environ.get("GEMINI_MODEL")
    if not api_key or not primary:
        return components  # heuristic labels from group.py stand as-is

    fallback = (os.environ.get("GEMINI_FALLBACK_MODEL") or "").strip()
    models = [primary]
    if fallback and fallback != primary:
        models.append(fallback)

    body = json.dumps({
        "contents": [{"parts": [{"text": _build_prompt(components)}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")

    deadline = time.monotonic() + _TOTAL_DEADLINE_SECONDS

    for model in models:
        for attempt in range(_ATTEMPTS_PER_MODEL):
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                logger.warning("llm: deadline reached, using heuristic labels")
                return components

            payload, retryable, note = _call_once(
                model, api_key, body, min(_PER_ATTEMPT_TIMEOUT_SECONDS, remaining)
            )

            if payload is not None:
                text = _extract_text(payload)
                labels = _parse_llm_json(text, components) if text else None
                if labels is not None:
                    logger.info("llm: success model=%s attempt=%d", model, attempt + 1)
                    enriched = []
                    for comp in components:
                        name, summary = labels[comp.id]
                        new_label = ComponentLabel(name=name, summary=summary, source=LabelSource.llm)
                        enriched.append(comp.model_copy(update={"label": new_label}))
                    return enriched
                # got a response but unusable (blocked / malformed / wrong ids)
                note, retryable = "unusable response", True

            logger.warning("llm: model=%s attempt=%d failed (%s)", model, attempt + 1, note)

            if not retryable:
                break  # e.g. 400/401/403/404 — retrying same model is pointless
            if attempt < _ATTEMPTS_PER_MODEL - 1:
                time.sleep(min(_BACKOFF_SECONDS[attempt], max(0.0, deadline - time.monotonic())))

    return components
