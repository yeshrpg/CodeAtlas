"""
CodeAtlas — repo file scanner.

Walks an already-fetched/extracted repo directory and produces the flat
file list that parse_py.py / JS-TS parser will consume in Y3.

Locked constraints reflected here:
- Caps: 100MB total repo size, 3000 files max, skip any single file > 300KB.
- Skip-list directories: node_modules, venv, dist, build, .git, __pycache__,
  vendor, tests (matched anywhere in the relative path, not just at root).
- All emitted paths are POSIX (.as_posix()) regardless of host OS.
- Only .py/.js/.jsx/.ts/.tsx files are scanned for parsing; everything else
  is counted but not included in `files` (kept out of the parse pipeline).
- Plain functions, no `async def`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

MAX_TOTAL_SIZE_BYTES = 100 * 1024 * 1024  # 100MB, per locked spec
MAX_FILE_COUNT = 3000
MAX_SINGLE_FILE_BYTES = 300 * 1024  # 300KB — files larger than this are skipped
FLAT_REPO_FILE_THRESHOLD = 25  # if <=25 files total and none nested, flat-repo guard trips

SKIP_DIR_NAMES = {
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".git",
    "__pycache__",
    "vendor",
    "tests",
}

PARSEABLE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


class ScanError(Exception):
    """Raised when the repo cannot be scanned at all, or exceeds a hard cap."""


@dataclass
class ScannedFile:
    path: str  # POSIX, relative to repo root
    absolute_path: str  # POSIX, absolute on-disk path (for the parser to open)
    language: str  # "python" | "javascript" | "typescript"
    size_bytes: int


@dataclass
class ScanResult:
    files: list[ScannedFile] = field(default_factory=list)
    total_files_scanned: int = 0  # parseable files actually included
    total_files_skipped: int = 0  # skipped for size, extension, or skip-dir
    total_size_bytes: int = 0  # sum of size_bytes for included files only
    is_flat_repo: bool = False


def _is_within_skip_dir(rel_parts: tuple[str, ...]) -> bool:
    # Skip if any path component (except the filename itself) matches a
    # skip-dir name. rel_parts includes the filename as the last element.
    return any(part in SKIP_DIR_NAMES for part in rel_parts[:-1])


def scan_repo(repo_root: str) -> ScanResult:
    """
    Walk `repo_root` (an absolute path to an already-extracted repo), apply
    caps and the skip-list, and return the set of parseable files plus stats.

    Raises ScanError if the repo has zero parseable files after filtering,
    or if MAX_FILE_COUNT is exceeded even after skip-dir filtering (a
    pathological repo we refuse to analyze rather than silently truncate).
    """
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ScanError(f"Repo root does not exist or is not a directory: {repo_root}")

    result = ScanResult()
    candidate_count = 0  # files that pass the skip-dir + extension filter, before size check

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel = path.relative_to(root)
        rel_parts = rel.parts
        rel_posix = rel.as_posix()

        if _is_within_skip_dir(rel_parts):
            result.total_files_skipped += 1
            continue

        ext = path.suffix.lower()
        if ext not in PARSEABLE_EXTENSIONS:
            result.total_files_skipped += 1
            continue

        candidate_count += 1
        if candidate_count > MAX_FILE_COUNT:
            raise ScanError(
                f"Repository has more than {MAX_FILE_COUNT} parseable files; refusing to analyze."
            )

        size_bytes = path.stat().st_size
        if size_bytes > MAX_SINGLE_FILE_BYTES:
            result.total_files_skipped += 1
            continue

        if result.total_size_bytes + size_bytes > MAX_TOTAL_SIZE_BYTES:
            raise ScanError(
                f"Repository total size exceeds the {MAX_TOTAL_SIZE_BYTES / 1024 / 1024:.0f}MB limit."
            )

        result.files.append(
            ScannedFile(
                path=rel_posix,
                absolute_path=path.as_posix(),
                language=PARSEABLE_EXTENSIONS[ext],
                size_bytes=size_bytes,
            )
        )
        result.total_size_bytes += size_bytes

    result.total_files_scanned = len(result.files)

    if result.total_files_scanned == 0:
        raise ScanError("No parseable Python/JS/TS files found in this repository.")

    # Flat-repo guard: small repo with no meaningful folder nesting (i.e. all
    # files sit directly at the repo root) — grouping (Y4) needs to know this
    # so it can fall back to a single component instead of forcing 5-25.
    has_nesting = any(len(Path(f.path).parts) > 1 for f in result.files)
    result.is_flat_repo = (
        result.total_files_scanned <= FLAT_REPO_FILE_THRESHOLD and not has_nesting
    )

    return result
