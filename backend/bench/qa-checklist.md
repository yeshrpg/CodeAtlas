# QA Checklist: Test 10 Random Public Repos

## Purpose
Run CodeAtlas on 10 diverse public repos to find crashes, timeouts, and ugly graphs.

## Test Matrix

| # | Repo | Size | Language | Status | Issues | Notes |
|---|------|------|----------|--------|--------|-------|
| 1 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 2 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 3 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 4 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 5 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 6 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 7 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 8 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 9 | (to fill) | (to fill) | (to fill) | PENDING | — | — |
| 10 | (to fill) | (to fill) | (to fill) | PENDING | — | — |

---

## Failure Categories

### 🔴 CRASH (Stop Analysis)
Parser crashes, unhandled exception, app throws error.

**Action:** Fix parser, re-test

### 🟡 TIMEOUT (>15s)
Analysis takes > 15 seconds.

**Causes:** Large repo, slow Groq, slow GitHub

**Action:** Log time, note in "Notes" column

### 🟡 UGLY GRAPH
- Over 25 components (merged into "other")
- Over 50 edges (hard to read)
- Many unresolved imports (>10%)
- All heuristic labels (LLM failed)

**Action:** Log in "Issues", note in "Notes"

---

## How to Test One Repo

```bash
# 1. Pick a random public repo
# 2. Paste URL into CodeAtlas UI
# 3. Click Analyze
# 4. Wait for result

# Check for:
# ✅ Diagram renders without errors
# ✅ L1 diagram has 5-25 components
# ✅ L2 drill-down works
# ✅ Click edge shows evidence
# ✅ Export works (copy .mmd, download SVG)
# ✅ Analysis time < 15s

# If anything breaks, note it:
# - What happened? (crash, timeout, ugly)
# - Which repo? (name + URL)
# - Any error message? (paste here)
```

---

## Example Test Run

### Run 1: lodash/lodash
- **Repo:** https://github.com/lodash/lodash
- **Size:** ~150 KB
- **Language:** JavaScript
- **Status:** ✅ PASS
- **Issues:** None
- **Time:** 1.2s
- **Components:** 8
- **Notes:** Small, clean, fast

### Run 2: django/django
- **Repo:** https://github.com/django/django
- **Size:** ~2 MB
- **Language:** Python
- **Status:** ⚠️ WARN
- **Issues:** Timeout (18s)
- **Time:** 18.3s
- **Components:** 12
- **Notes:** Large repo. Groq was slow, but heuristic fallback saved it. Still rendered.

### Run 3: microsoft/TypeScript
- **Repo:** https://github.com/microsoft/TypeScript
- **Size:** ~1.5 MB
- **Language:** TypeScript
- **Status:** ⚠️ WARN
- **Issues:** Ugly graph (many unresolved)
- **Time:** 2.1s
- **Components:** 25 (merged to limit)
- **Unresolved:** 12%
- **Notes:** Path aliases not resolved yet. Still readable with heuristic labels.

---

## Summary Template

After testing 10 repos, fill this: