"""
CodeAtlas backend — FastAPI entrypoint.

Locked constraints reflected here:
- All endpoints are plain `def`, never `async def`.
- CORS allowlist comes from the ALLOWED_ORIGINS env var (comma-separated),
  never hardcoded or wildcarded in production.
- No SSE, no SQLite — in-memory dict cache only (wired in later Y-steps).
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schema import AnalysisResult, AnalysisStatus

APP_NAME = "codeatlas-backend"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# --- CORS -------------------------------------------------------------
# ALLOWED_ORIGINS is a comma-separated list, e.g.:
#   ALLOWED_ORIGINS=https://codeatlas-frontend.onrender.com,http://localhost:5173
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
# Simple dict cache keyed by analysis_id. Populated by later Y-steps
# (fetch/scan/parse/group/llm pipeline). Kept here so /health and future
# route modules share one process-wide store without a DB.
ANALYSIS_CACHE: dict[str, AnalysisResult] = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "allowed_origins_configured": len(ALLOWED_ORIGINS),
        "cached_analyses": len(ANALYSIS_CACHE),
    }


# NOTE: /analyze, /analysis/{id}, /compare routes land in Y7 (main.py/deploy
# wrap-up) once fetch.py, scan.py, parse_py.py, resolve.py, group.py,
# mermaid.py and llm_client.py exist. This file intentionally stays minimal
# for Y1 so /health can be deployed and smoke-tested on Render immediately.
