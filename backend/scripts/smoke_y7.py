"""
Local smoke test for Y7. Runs the real pipeline (real GitHub fetch + real Gemini).

Run from the backend/ folder:
    python scripts/smoke_y7.py <owner> <name> [ref]
e.g.
    python scripts/smoke_y7.py miguelgrinberg microblog

Needs GEMINI_API_KEY / GEMINI_MODEL (and optionally GITHUB_TOKEN) in env or backend/.env
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from app.pipeline import run_analysis  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    owner, name = sys.argv[1], sys.argv[2]
    ref = sys.argv[3] if len(sys.argv) > 3 else None

    r = run_analysis(owner, name, ref)
    print(f"status        : {r.status.value}")
    if r.error:
        print(f"error         : {r.error}")
    print(f"commit        : {r.repo.commit_sha[:10]} ({r.repo.default_branch})")
    print(f"files scanned : {r.repo.total_files_scanned}  skipped: {r.repo.total_files_skipped}  flat: {r.repo.is_flat_repo}")
    print(f"parsed files  : {len(r.parsed_files)}  parse_errors: {sum(1 for p in r.parsed_files if p.parse_error)}")
    print(f"components    : {len(r.components)}   edges: {len(r.edges)}   unresolved imports: {len(r.unresolved.imports)}")
    print(f"llm           : model={r.llm_model} calls={r.llm_call_count}")
    for c in r.components:
        print(f"  - [{c.label.source.value:9}] {c.folder_path or '.'}: {c.label.name} — {c.label.summary}")
    if r.mermaid:
        print("\n--- mermaid ---")
        print(r.mermaid.source)
    return 0 if r.status.value == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
