"""
CodeAtlas — GitHub zipball fetch + safe extraction.

Locked constraints reflected here:
- Public repos only (no auth flows beyond a read-only token for rate limits).
- 100MB total repo size cap, enforced both on the Content-Length header
  (fast fail before downloading) and on actual bytes read (fast fail if a
  server lies about Content-Length).
- Zip-slip safe extraction: every member path is validated to stay inside
  the extraction root before being written.
- All returned/extracted paths are POSIX (.as_posix()).
- Plain functions, no `async def` anywhere in this codebase.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

GITHUB_API_BASE = "https://api.github.com"
MAX_REPO_SIZE_BYTES = 100 * 1024 * 1024  # 100MB, per locked spec
DOWNLOAD_CHUNK_BYTES = 1024 * 1024  # 1MB streaming chunks
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_SECONDS = 30.0


class FetchError(Exception):
    """Raised for any user-facing fetch failure (bad repo, too large, private, etc)."""


@dataclass
class FetchResult:
    owner: str
    name: str
    ref: str
    commit_sha: str
    extract_root: str  # POSIX absolute path to the extracted repo root
    total_size_bytes: int


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codeatlas-backend",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_repo_metadata(owner: str, name: str, client: httpx.Client) -> dict:
    """Fetch repo metadata; also used to confirm the repo is public and to
    resolve the default branch when no ref is given."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{name}"
    resp = client.get(url, headers=_github_headers(), timeout=REQUEST_TIMEOUT_SECONDS)

    if resp.status_code == 404:
        raise FetchError(f"Repository '{owner}/{name}' not found (or private/inaccessible).")
    if resp.status_code == 403:
        raise FetchError("GitHub API rate limit hit or token lacks access. Try again later.")
    resp.raise_for_status()

    data = resp.json()
    if data.get("private", False):
        raise FetchError(f"Repository '{owner}/{name}' is private. Only public repos are supported.")
    return data


def _get_commit_sha(owner: str, name: str, ref: str, client: httpx.Client) -> str:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{name}/commits/{ref}"
    resp = client.get(
        url,
        headers={**_github_headers(), "Accept": "application/vnd.github.sha"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if resp.status_code == 404:
        raise FetchError(f"Ref '{ref}' not found on '{owner}/{name}'.")
    resp.raise_for_status()
    # With the sha media type GitHub returns the raw sha as the body text.
    sha = resp.text.strip()
    if not sha:
        raise FetchError(f"Could not resolve commit sha for ref '{ref}'.")
    return sha


def _download_zipball(owner: str, name: str, ref: str, dest_zip_path: Path, client: httpx.Client) -> int:
    """Stream the zipball to disk, enforcing the size cap as bytes arrive.
    Returns total bytes written."""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{name}/zipball/{ref}"

    with client.stream(
        "GET",
        url,
        headers=_github_headers(),
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as resp:
        if resp.status_code == 404:
            raise FetchError(f"Zipball not found for '{owner}/{name}' at ref '{ref}'.")
        resp.raise_for_status()

        content_length = resp.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_REPO_SIZE_BYTES:
            raise FetchError(
                f"Repository archive is {int(content_length) / 1024 / 1024:.1f}MB, "
                f"exceeding the {MAX_REPO_SIZE_BYTES / 1024 / 1024:.0f}MB limit."
            )

        total_bytes = 0
        with open(dest_zip_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=DOWNLOAD_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > MAX_REPO_SIZE_BYTES:
                    raise FetchError(
                        f"Repository archive exceeded the "
                        f"{MAX_REPO_SIZE_BYTES / 1024 / 1024:.0f}MB limit during download."
                    )
                f.write(chunk)

        return total_bytes


def _safe_extract(zip_path: Path, extract_root: Path) -> None:
    """Extract a zip file, guarding against zip-slip path traversal and
    against decompression-bomb style blowups (checked via MAX_REPO_SIZE_BYTES
    on the sum of uncompressed member sizes)."""
    extract_root.mkdir(parents=True, exist_ok=True)
    resolved_root = extract_root.resolve()

    with zipfile.ZipFile(zip_path) as zf:
        total_uncompressed = sum(m.file_size for m in zf.infolist())
        if total_uncompressed > MAX_REPO_SIZE_BYTES:
            raise FetchError(
                f"Repository uncompressed size ({total_uncompressed / 1024 / 1024:.1f}MB) "
                f"exceeds the {MAX_REPO_SIZE_BYTES / 1024 / 1024:.0f}MB limit."
            )

        for member in zf.infolist():
            member_path = (resolved_root / member.filename).resolve()
            if not str(member_path).startswith(str(resolved_root) + os.sep) and member_path != resolved_root:
                raise FetchError(f"Refusing to extract unsafe path: {member.filename!r}")

        zf.extractall(resolved_root)


def _find_single_top_level_dir(extract_root: Path) -> Path:
    """GitHub zipballs always contain exactly one top-level dir named
    '{owner}-{repo}-{short_sha}'. Return it (as the actual repo root)."""
    entries = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(entries) != 1:
        raise FetchError(
            f"Expected exactly one top-level directory in the extracted zipball, found {len(entries)}."
        )
    return entries[0]


def fetch_repo(owner: str, name: str, ref: Optional[str], work_dir: str) -> FetchResult:
    """
    Fetch and safely extract a public GitHub repo at `ref` (branch/tag/sha),
    or the default branch if `ref` is None.

    `work_dir` is a caller-provided scratch directory (e.g. a per-analysis
    tempdir); this function does not clean it up.
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    with httpx.Client(max_redirects=MAX_REDIRECTS) as client:
        meta = _get_repo_metadata(owner, name, client)
        resolved_ref = ref or meta.get("default_branch", "main")
        commit_sha = _get_commit_sha(owner, name, resolved_ref, client)

        zip_path = work_path / "repo.zip"
        total_bytes = _download_zipball(owner, name, resolved_ref, zip_path, client)

        extract_root = work_path / "extracted"
        _safe_extract(zip_path, extract_root)
        repo_root = _find_single_top_level_dir(extract_root)

    zip_path.unlink(missing_ok=True)

    return FetchResult(
        owner=owner,
        name=name,
        ref=resolved_ref,
        commit_sha=commit_sha,
        extract_root=repo_root.resolve().as_posix(),
        total_size_bytes=total_bytes,
    )
