# CodeAtlas Benchmark Results

## Test Environment
- Date: 2026-09-26
- CodeAtlas Version: v1.0.0
- Event: UNMAKE 2026 Problem 09

## Benchmark Metrics

| Repo | Language | Recall | Precision | Unresolved % | Time (ms) | Heuristic Used |
|------|----------|--------|-----------|--------------|-----------|---|
| fastapi/full-stack | Python | 92% | 96% | 1.2% | 2,068 | No |
| expressjs/express | JavaScript | 87% | 93% | 3.8% | 2,042 | No |
| pallets/flask | Python | 88% | 94% | 2.1% | 2,045 | No |
| vuejs/vue | JavaScript | 78% | 91% | 8.5% | 2,042 | Yes |
| facebook/react | JavaScript | 85% | 89% | 5.2% | 2,059 | Yes |

## Metrics Summary
- **Avg Recall:** 86%
- **Avg Precision:** 92.6%
- **Avg Time:** 2,051ms (~2s)
- **Unresolved Imports:** 0-8.5% (mostly aliases and dynamic imports)
- **Heuristic Fallback Rate:** 40% (2/5 repos)

## Notes
- All repos analyzed successfully
- Response times stable (~2s)
- Large/complex repos (Vue, React) needed heuristic fallback
- Unresolved % expected on alias-heavy codebases