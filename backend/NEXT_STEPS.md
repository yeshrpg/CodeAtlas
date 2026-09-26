# Next Steps for Sv4 & Sv5 Completion

## When YESH's API is Ready (Real Pipeline Integrated)

### Sv4 - Generate Real Demo JSONs (1 hour)

```powershell
cd backend
python api_test_helper.py
```

This will:
- Analyze 3 demo repos (fastapi, express, flask)
- Save real JSON to `backend/demo_data/`
- Verify each loads in UI at http://localhost:5173

### Sv5 - Measure Real Precision/Recall (1-2 hours)

```powershell
cd backend

# 1. Re-clone 5 benchmark repos
mkdir benchmark_repos
cd benchmark_repos
git clone --depth 1 https://github.com/fastapi/full-stack-fastapi-template.git
git clone --depth 1 https://github.com/expressjs/express.git
git clone --depth 1 https://github.com/pallets/flask.git
git clone --depth 1 https://github.com/vuejs/vue.git
git clone --depth 1 https://github.com/facebook/react.git
cd ..

# 2. Generate reference graphs
cd benchmark_repos/expressjs-express
npx madge --extensions js,jsx,ts,tsx --json > reference.json
cd ../fastapi-full-stack-fastapi-template
python -c "import grimp, json; graph = grimp.build_graph('.'); edges = {node: list(graph.find_modules_directly_imported_by(node)) for node in graph.modules}; json.dump(edges, open('reference.json', 'w'), indent=2)"
cd ../..

# 3. Compare reference vs API output
python bench/measure_precision_recall.py

# 4. Manually verify 30 random edges per repo
#    (Open evidence panel in UI, confirm imports exist)

# 5. Update bench/results.md with real numbers
```

### Sv6 - Finalize Docs (30 min)

1. Add real screenshot to README.md
2. Commit final work

```powershell
git commit -m "final: real data from Sv4/Sv5 + screenshots"
```

---

## Current Status

✅ All code written and tested
✅ Measurement script ready (measure_precision_recall.py)
✅ Helpers prepared (api_test_helper.py, benchmark_helper.py)
⏳ Waiting for YESH's real `/analyze` endpoint
⏳ Waiting for parser integration

---

## Files Ready

- `backend/bench/measure_precision_recall.py` - Precision/recall measurement
- `backend/api_test_helper.py` - Demo JSON generation
- `backend/benchmark_helper.py` - Measurement helpers
- `backend/NEXT_STEPS.md` - This file (quickstart guide)

---

## Estimated Timeline

Once YESH confirms pipeline is ready:
- Sv4: 1 hour (generate + verify demo JSONs)
- Sv5: 1-2 hours (re-clone, generate refs, measure precision/recall)
- Sv6: 30 min (add screenshots + commit)
- **Total: 2.5-3.5 hours**

---

## Quick Start Once API is Live

```powershell
cd backend
python api_test_helper.py      # Sv4: Generate demo JSONs
python benchmark_helper.py      # Sv5: Measure on repos
# Update README with screenshot
git commit -m "final: real Sv4/Sv5 data"
```