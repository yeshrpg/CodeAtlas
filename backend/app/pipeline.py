"""
CodeAtlas — analysis pipeline (Y7).

fetch -> scan -> parse (.py) -> resolve -> group -> edges -> ONE LLM call -> mermaid

`run_analysis` NEVER raises. Every failure comes back as an AnalysisResult
with status=failed and a user-safe `error` message, so the API layer can
return it as normal JSON instead of a raw 500.

Locked constraints reflected here:
- ONE Gemini call per analysis (inside enrich_components; it falls back to
  heuristic labels on its own, so a dead LLM never fails the analysis).
- LLM never decides edges or Mermaid; both are built by our own code.
- Plain functions, no async. POSIX paths only.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.schema import (
    AnalysisResult,
    AnalysisStatus,
    LabelSource,
    RepoMeta,
)
from app.services.fetch import FetchError, FetchResult, fetch_repo
from app.services.group import build_components, build_edges
from app.services.llm_client import enrich_components
from app.services.mermaid import render_mermaid
from app.services.parse_py import parse_python_file
from app.services.resolve import resolve_all
from app.services.scan import ScanError, ScanResult, scan_repo

log = logging.getLogger("codeatlas.pipeline")


class PipelineError(Exception):
    """User-facing pipeline failure (message is safe to show in the UI)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _failed(
    analysis_id: str,
    owner: str,
    name: str,
    ref: Optional[str],
    created_at: datetime,
    message: str,
    fetched: Optional[FetchResult] = None,
    scan: Optional[ScanResult] = None,
) -> AnalysisResult:
    repo = RepoMeta(
        owner=owner,
        name=name,
        default_branch=fetched.ref if fetched else (ref or "unknown"),
        commit_sha=fetched.commit_sha if fetched else "",
        is_public=fetched is not None,  # fetch_repo rejects private repos
        total_files_scanned=scan.total_files_scanned if scan else 0,
        total_files_skipped=scan.total_files_skipped if scan else 0,
        total_size_bytes=fetched.total_size_bytes if fetched else 0,
        is_flat_repo=scan.is_flat_repo if scan else False,
    )
    return AnalysisResult(
        analysis_id=analysis_id,
        status=AnalysisStatus.failed,
        repo=repo,
        created_at=created_at,
        completed_at=_now(),
        error=message,
    )


def run_analysis(
    owner: str,
    name: str,
    ref: Optional[str] = None,
    analysis_id: Optional[str] = None,
) -> AnalysisResult:
    analysis_id = analysis_id or uuid.uuid4().hex
    created_at = _now()
    work_dir = tempfile.mkdtemp(prefix="codeatlas_")

    fetched: Optional[FetchResult] = None
    scan: Optional[ScanResult] = None
    error_message: Optional[str] = None

    try:
        fetched = fetch_repo(owner, name, ref, work_dir)
        scan = scan_repo(fetched.extract_root)
        repo_root = Path(fetched.extract_root)

        # Python only for now. JS/TS files are scanned/counted but not parsed
        # until Satvik's extractor is wired in.
        raw_files = []
        for f in scan.files:
            if f.language != "python":
                continue
            try:
                raw_files.append(parse_python_file(Path(f.absolute_path), repo_root))
            except Exception:  # one bad file must not sink the analysis
                log.exception("parse_python_file crashed on %s; skipping", f.path)

        if not raw_files:
            raise PipelineError(
                "No parseable Python files found (JS/TS analysis is not enabled yet)."
            )

        parsed_files, unresolved = resolve_all(raw_files)
        components = build_components(parsed_files, scan.is_flat_repo)
        edges = build_edges(components, parsed_files)

        components = enrich_components(components)  # the ONE LLM call (self-falls-back)
        mermaid = render_mermaid(components, edges)

        llm_used = any(c.label.source == LabelSource.llm for c in components)

        return AnalysisResult(
            analysis_id=analysis_id,
            status=AnalysisStatus.done,
            repo=RepoMeta(
                owner=owner,
                name=name,
                default_branch=fetched.ref,  # resolved ref (default branch if none given)
                commit_sha=fetched.commit_sha,
                is_public=True,
                total_files_scanned=scan.total_files_scanned,
                total_files_skipped=scan.total_files_skipped,
                total_size_bytes=fetched.total_size_bytes,
                is_flat_repo=scan.is_flat_repo,
            ),
            created_at=created_at,
            completed_at=_now(),
            parsed_files=parsed_files,
            components=components,
            edges=edges,
            unresolved=unresolved,
            mermaid=mermaid,
            llm_model=os.environ.get("GEMINI_MODEL") if llm_used else None,
            llm_call_count=1 if llm_used else 0,
        )

    except (FetchError, ScanError, PipelineError) as exc:
        error_message = str(exc)
    except ValidationError:
        # Most common cause: repo too small/shallow to form 5-25 components.
        log.exception("Schema validation failed for %s/%s", owner, name)
        error_message = (
            "Could not build a valid architecture map for this repo "
            "(it may be too small or too shallow to form 5-25 components)."
        )
    except Exception:
        log.exception("Unexpected failure analyzing %s/%s", owner, name)
        error_message = "Unexpected internal error while analyzing this repository."
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return _failed(analysis_id, owner, name, ref, created_at, error_message, fetched, scan)
