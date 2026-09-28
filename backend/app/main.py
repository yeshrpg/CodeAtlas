"""
CodeAtlas backend — FastAPI entrypoint.

Locked constraints reflected here:
- All endpoints are plain `def`, never `async def`.
- CORS allowlist comes from the ALLOWED_ORIGINS env var (comma-separated),
  never hardcoded or wildcarded in production.
- No SSE, no SQLite — in-memory dict cache only.
"""

import os
import threading
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.pipeline import run_analysis
from app.schema import AnalysisResult

APP_NAME = "codeatlas-backend"
APP_VERSION = "0.2.0"

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

# --- In-memory cache ----------------------------------------------------
# Keyed by analysis_id. Capped (oldest evicted first) so a long-running
# Render free-tier instance can't grow without bound.
MAX_CACHED_ANALYSES = 50
ANALYSIS_CACHE: dict[str, AnalysisResult] = {}
_CACHE_LOCK = threading.Lock()


def _cache_put(result: AnalysisResult) -> None:
    with _CACHE_LOCK:
        while len(ANALYSIS_CACHE) >= MAX_CACHED_ANALYSES:
            ANALYSIS_CACHE.pop(next(iter(ANALYSIS_CACHE)))
        ANALYSIS_CACHE[result.analysis_id] = result


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
    }


@app.post("/analyze", response_model=AnalysisResult)
def analyze(req: AnalyzeRequest) -> AnalysisResult:
    """Runs the full pipeline synchronously. Pipeline failures come back as
    HTTP 200 with status="failed" + `error`; only bad input gets a 422."""
    result = run_analysis(req.owner, req.name, req.ref)
    _cache_put(result)
    return result


@app.get("/analysis/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str) -> AnalysisResult:
    result = ANALYSIS_CACHE.get(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found (expired or never existed).")
    return result


# NOTE: /compare lands in Y8 (stretch).
