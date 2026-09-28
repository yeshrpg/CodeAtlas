"""
CodeAtlas backend — FastAPI entrypoint.

Locked constraints reflected here:
- All endpoints are plain `def`, never `async def`.
- CORS allowlist comes from the ALLOWED_ORIGINS env var (comma-separated),
  never hardcoded or wildcarded in production.
- No SSE, no SQLite — in-memory dict cache only.

v0.3.1:
- Concurrency cap + per-repo result cache (demo-day safety on Render free tier).
- Results where the LLM fell back to heuristic labels are cached for only
  HEURISTIC_TTL_SECONDS, so a Gemini hiccup/misconfig never sticks for 15 min.
- /health reports llm_configured; /debug/llm diagnoses Gemini key/model problems
  (temporary; returns no secrets; rate-limited to one Gemini call per 30s).
"""

import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.pipeline import run_analysis
from app.schema import AnalysisResult, AnalysisStatus, RepoMeta

APP_NAME = "codeatlas-backend"
APP_VERSION = "0.3.1"

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# --- CORS -------------------------------------------------------------
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# --- In-memory stores -----------------------------------------------------
MAX_CACHED_ANALYSES = 50
MAX_CONCURRENT_ANALYSES = 2
BUSY_WAIT_SECONDS = 45
LLM_RESULT_TTL_SECONDS = 15 * 60  # results with real LLM labels
HEURISTIC_TTL_SECONDS = 60  # results where the LLM step fell back

ANALYSIS_CACHE: dict[str, AnalysisResult] = {}  # analysis_id -> result
_RESULT_INDEX: dict[tuple[str, str, str], tuple[float, str]] = {}  # key -> (expires_at, analysis_id)
_CACHE_LOCK = threading.Lock()
_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_ANALYSES)


def _cache_put(result: AnalysisResult, key: Optional[tuple[str, str, str]] = None, ttl: float = 0) -> None:
    with _CACHE_LOCK:
        while len(ANALYSIS_CACHE) >= MAX_CACHED_ANALYSES:
            ANALYSIS_CACHE.pop(next(iter(ANALYSIS_CACHE)))
        ANALYSIS_CACHE[result.analysis_id] = result
        if key is not None and ttl > 0:
            while len(_RESULT_INDEX) >= 200:
                _RESULT_INDEX.pop(next(iter(_RESULT_INDEX)))
            _RESULT_INDEX[key] = (time.time() + ttl, result.analysis_id)


def _cache_get(key: tuple[str, str, str]) -> Optional[AnalysisResult]:
    with _CACHE_LOCK:
        entry = _RESULT_INDEX.get(key)
        if entry is None:
            return None
        expires_at, analysis_id = entry
        if time.time() > expires_at:
            _RESULT_INDEX.pop(key, None)
            return None
        return ANALYSIS_CACHE.get(analysis_id)


def _busy_result(req: "AnalyzeRequest") -> AnalysisResult:
    now = datetime.now(timezone.utc)
    return AnalysisResult(
        analysis_id=uuid.uuid4().hex,
        status=AnalysisStatus.failed,
        repo=RepoMeta(
            owner=req.owner,
            name=req.name,
            default_branch=req.ref or "unknown",
            commit_sha="",
            is_public=False,
            total_files_scanned=0,
            total_files_skipped=0,
            total_size_bytes=0,
        ),
        created_at=now,
        completed_at=now,
        error="Server is busy analyzing other repositories. Please try again in a minute.",
    )


# --- Request models -------------------------------------------------------
# Strict patterns: owner/name/ref get interpolated into GitHub API URLs.
class AnalyzeRequest(BaseModel):
    owner: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    ref: Optional[str] = Field(default=None, max_length=200, pattern=r"^[A-Za-z0-9_./-]+$")


# --- Routes -------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "allowed_origins_configured": len(ALLOWED_ORIGINS),
        "cached_analyses": len(ANALYSIS_CACHE),
        "llm_configured": bool(os.environ.get("GEMINI_API_KEY", "").strip())
        and bool(os.environ.get("GEMINI_MODEL", "").strip()),
    }


@app.post("/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest, fresh: bool = False) -> AnalysisResult:
    """Runs the full pipeline synchronously. Pipeline failures come back as
    HTTP 200 with status="failed" + `error`; only bad input gets a 422.
    A recent successful result for the same (owner, name, ref) is returned
    instantly unless ?fresh=true."""
    key = (req.owner.lower(), req.name.lower(), req.ref or "")

    if not fresh:
        cached = _cache_get(key)
        if cached is not None:
            return cached

    if not _SLOTS.acquire(timeout=BUSY_WAIT_SECONDS):
        return _busy_result(req)
    try:
        result = run_analysis(req.owner, req.name, req.ref)
    finally:
        _SLOTS.release()

    if result.status == AnalysisStatus.done:
        ttl = LLM_RESULT_TTL_SECONDS if result.llm_call_count == 1 else HEURISTIC_TTL_SECONDS
        _cache_put(result, key, ttl)
    else:
        _cache_put(result)  # retrievable by id, never reused for new requests
    return result


@app.get("/analysis/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str) -> AnalysisResult:
    result = ANALYSIS_CACHE.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found (expired or never existed).")
    return result


# --- Temporary diagnostics (remove after the LLM step is confirmed) --------
_last_debug_call = 0.0


@app.get("/debug/llm")
def debug_llm():
    """Reports whether GEMINI_API_KEY / GEMINI_MODEL are set sanely and whether
    Google accepts them. Never returns the key. One Gemini call per 30s max."""
    global _last_debug_call
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "")
    info: dict = {
        "api_key_set": bool(key.strip()),
        "api_key_length": len(key),
        "api_key_has_space_or_quote": key != key.strip() or '"' in key or "'" in key,
        "model": model,
        "model_has_space_or_quote": model != model.strip() or '"' in model or "'" in model,
    }
    if not key.strip() or not model.strip():
        info["verdict"] = "MISSING: GEMINI_API_KEY and/or GEMINI_MODEL not set in Render env"
        return info

    now = time.time()
    if now - _last_debug_call < 30:
        info["verdict"] = "rate-limited: wait 30s and retry"
        return info
    _last_debug_call = now

    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model.strip()}:generateContent",
            headers={"x-goog-api-key": key.strip(), "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": "Reply with the single word: ok"}]}]},
            timeout=20,
        )
        info["http_status"] = resp.status_code
        if resp.status_code == 200:
            info["verdict"] = "OK: Gemini accepts this key + model"
        else:
            try:
                info["google_error"] = str(resp.json().get("error", {}).get("message", ""))[:300]
            except Exception:
                info["google_error"] = resp.text[:300]
            info["verdict"] = "GOOGLE REJECTED THE CALL: see http_status and google_error"
    except Exception as exc:
        info["http_error"] = f"{type(exc).__name__}: {exc}"[:300]
        info["verdict"] = "NETWORK ERROR reaching Google"
    return info


# NOTE: /compare lands in Y8 (stretch).
