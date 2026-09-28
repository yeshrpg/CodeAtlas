from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

MAX_TOTAL_SIZE_BYTES = 100 * 1024 * 1024
MAX_FILE_COUNT = 3000
MAX_SINGLE_FILE_BYTES = 300 * 1024
FLAT_REPO_FILE_THRESHOLD = 25

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
    pass

@dataclass
class ScannedFile:
    path: str
    absolute_path: str
    language: str
    size_bytes: int

@dataclass
class ScanResult:
    files: list[ScannedFile] = field(default_factory=list)
    total_files_scanned: int = 0
    total_files_skipped: int = 0
    total_size_bytes: int = 0
    is_flat_repo: bool = False

def _is_within_skip_dir(rel_parts: tuple[str, ...]) -> bool:
    return any(part in SKIP_DIR_NAMES for part in rel_parts[:-1])

def scan_repo(repo_root: str) -> ScanResult:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ScanError(f"Repo root does not exist or is not a directory: {repo_root}")

    result = ScanResult()
    candidate_count = 0

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
            raise ScanError(f"Repository has more than {MAX_FILE_COUNT} parseable files; refusing to analyze.")

        size_bytes = path.stat().st_size
        if size_bytes > MAX_SINGLE_FILE_BYTES:
            result.total_files_skipped += 1
            continue

        if result.total_size_bytes + size_bytes > MAX_TOTAL_SIZE_BYTES:
            raise ScanError(f"Repository total size exceeds the {MAX_TOTAL_SIZE_BYTES / 1024 / 1024:.0f}MB limit.")

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

    has_nesting = any(len(Path(f.path).parts) > 1 for f in result.files)
    result.is_flat_repo = (
        result.total_files_scanned <= FLAT_REPO_FILE_THRESHOLD and not has_nesting
    )

    return result