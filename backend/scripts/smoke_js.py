"""
smoke_js.py - local check that the JS/TS parser works through the real pipeline.

Run from repo root (PowerShell):
    python backend\\scripts\\smoke_js.py gothinkster node-express-realworld-example-app
    python backend\\scripts\\smoke_js.py miguelgrinberg microblog        # regression: must match old numbers

It forces ENABLE_JS_PARSER=1 and removes GEMINI_API_KEY for this process only
(heuristic labels, zero Gemini calls), then prints the numbers that matter.
"""

from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

os.environ["ENABLE_JS_PARSER"] = "1"
os.environ.pop("GEMINI_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/

from app.pipeline import run_analysis  # noqa: E402
import app.pipeline as pipeline_mod  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: python backend\\scripts\\smoke_js.py <owner> <name> [ref]")
    owner, name = sys.argv[1], sys.argv[2]
    ref = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"parse_js_files importable: {pipeline_mod.parse_js_files is not None}")
    t0 = time.time()
    res = run_analysis(owner, name, ref)
    dt = time.time() - t0

    print(f"status={res.status.value if hasattr(res.status, 'value') else res.status}  time={dt:.1f}s")
    if res.error:
        print(f"error: {res.error}")
    langs = Counter(getattr(pf.language, "value", pf.language) for pf in res.parsed_files)
    errs = [pf.path for pf in res.parsed_files if pf.parse_error]
    print(f"files_scanned={res.repo.total_files_scanned} skipped={res.repo.total_files_skipped}")
    print(f"parsed_files={len(res.parsed_files)} by_language={dict(langs)} parse_errors={len(errs)}")
    print(f"components={len(res.components)} edges={len(res.edges)} unresolved={len(res.unresolved.imports) if res.unresolved else 0}")
    for c in res.components:
        print(f"  - {c.folder_path or '.'}: {len(c.files)} files")
    for e in res.edges[:8]:
        print(f"  edge {e.source_id} -> {e.target_id} x{e.import_count}")
    if errs:
        print("parse errors in:", errs[:5])


if __name__ == "__main__":
    main()
