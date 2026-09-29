"""
gen_demo_data.py — pre-generate LLM-labeled demo analyses from the LIVE backend.

Usage (from repo root, PowerShell):
    python backend\\scripts\\gen_demo_data.py miguelgrinberg/microblog owner/name ...

Env / flags:
    CODEATLAS_URL   default https://codeatlas-backend-a6jw.onrender.com
    --tries N       attempts per repo (default 8)
    --gap S         seconds between attempts (default 15; free tier ~5 RPM)

Behaviour:
  - wakes the backend via /health first (Render cold start ~50s)
  - POST /analyze?fresh=true, repeats until status == done AND llm_call_count == 1
    AND every component label source == "llm"
  - saves ONLY that good result to <repo root>/demo_data/<owner>__<name>.json
  - never overwrites an existing file with a worse (heuristic) result
  - prints the real numbers Rohan can quote
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("CODEATLAS_URL", "https://codeatlas-backend-a6jw.onrender.com").rstrip("/")
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "demo_data"


def http(method: str, path: str, body: dict | None = None, timeout: int = 150):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wake():
    print(f"[wake] {BASE}/health ...")
    for i in range(4):
        try:
            h = http("GET", "/health", timeout=90)
            print(f"[wake] ok: {h}")
            if not h.get("llm_configured"):
                print("[wake] WARNING: llm_configured is false on the server")
            return
        except Exception as e:  # noqa: BLE001
            print(f"[wake] attempt {i + 1} failed: {type(e).__name__}")
            time.sleep(5)
    sys.exit("backend not reachable")


def is_good(res: dict) -> bool:
    if res.get("status") != "done":
        return False
    if res.get("llm_call_count") != 1:
        return False
    comps = res.get("components") or []
    return bool(comps) and all((c.get("label") or {}).get("source") == "llm" for c in comps)


def existing_is_good(path: Path) -> bool:
    try:
        return is_good(json.loads(path.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return False


def run_repo(owner: str, name: str, tries: int, gap: int) -> bool:
    out = OUT_DIR / f"{owner}__{name}.json"
    for n in range(1, tries + 1):
        t0 = time.time()
        try:
            res = http("POST", "/analyze?fresh=true", {"owner": owner, "name": name})
            # if POST returns only a summary, pull the full result by id
            if "components" not in res and res.get("analysis_id"):
                res = http("GET", f"/analysis/{res['analysis_id']}")
        except urllib.error.HTTPError as e:
            print(f"[{owner}/{name}] try {n}/{tries}: HTTP {e.code} (input rejected or server error)")
            res = None
        except Exception as e:  # noqa: BLE001
            print(f"[{owner}/{name}] try {n}/{tries}: {type(e).__name__}")
            res = None
        elapsed = time.time() - t0

        if res is not None:
            status = res.get("status")
            comps = res.get("components") or []
            llm_n = sum(1 for c in comps if (c.get("label") or {}).get("source") == "llm")
            print(
                f"[{owner}/{name}] try {n}/{tries}: status={status} "
                f"llm_calls={res.get('llm_call_count')} llm_labels={llm_n}/{len(comps)} {elapsed:.1f}s"
            )
            if status == "failed":
                print(f"    error: {res.get('error')}")
                if "5-25" in str(res.get("error")) or "No Python" in str(res.get("error")):
                    return False  # deterministic failure, retrying won't help
            if is_good(res):
                OUT_DIR.mkdir(exist_ok=True)
                out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
                repo = res.get("repo", {})
                print(f"    SAVED {out.relative_to(REPO_ROOT)}")
                print(
                    f"    numbers: files_scanned={repo.get('total_files_scanned')} "
                    f"parsed={len(res.get('parsed_files') or [])} components={len(comps)} "
                    f"edges={len(res.get('edges') or [])} "
                    f"unresolved={len((res.get('unresolved') or {}).get('imports', []))} "
                    f"analysis_time~{elapsed:.0f}s"
                )
                return True

        if n < tries:
            time.sleep(gap)

    kept = "kept existing good file" if existing_is_good(out) else "nothing saved"
    print(f"[{owner}/{name}] gave up after {tries} tries ({kept})")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repos", nargs="+", help="owner/name")
    ap.add_argument("--tries", type=int, default=8)
    ap.add_argument("--gap", type=int, default=15)
    args = ap.parse_args()

    wake()
    ok = 0
    for r in args.repos:
        if "/" not in r:
            print(f"skip '{r}': expected owner/name")
            continue
        owner, name = r.split("/", 1)
        ok += run_repo(owner, name, args.tries, args.gap)
        time.sleep(args.gap)  # stay under Gemini RPM between repos
    print(f"\nDone: {ok}/{len(args.repos)} repos saved with LLM labels")
    sys.exit(0 if ok == len(args.repos) else 1)


if __name__ == "__main__":
    main()
