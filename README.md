# CodeAtlas: Code-to-Diagram Architecture Visualizer

## What is it?

Paste a GitHub repo URL → Get an interactive architecture diagram with real imports.

Every edge is clickable to see the exact file:line where the import happens. Compare two commits to see what changed architecturally in green/red.

Unlike tools that guess architecture from file structure, CodeAtlas **parses the actual code** to find real dependencies.

---

## How to Run Locally

### Prerequisites
- Python 3.11+
- Node LTS
- Git

### Setup

```bash
# Clone repo
git clone https://github.com/yeshrpg/CodeAtlas.git
cd CodeAtlas

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt
npm install  # Frontend

# Start backend
cd backend
python -m uvicorn app.main:app --reload

# In another terminal, start frontend
cd frontend
npm run dev

# Access at http://localhost:5173
```

---

## Architecture

### Backend (Python)
- **core/parse_js.py** - JavaScript/TypeScript import parser (regex + tree-sitter fallback)
- **core/parse_py.py** - Python import parser (ast module)
- **core/resolve.py** - Resolves imports to file paths with line numbers
- **core/group.py** - Folder-based component grouping (5-25 components)
- **core/mermaid.py** - Emits Mermaid diagram syntax
- **llm/client.py** - Groq API integration (one call per analysis)
- **llm/fallback.py** - Heuristic labels when LLM fails

### Frontend (React + Vite + Tailwind)
- L1 diagram: components and weighted edges
- L2 drill-down: files within one component
- Side panel: symbols, imports, summary
- Click edge → Evidence panel (file:line)
- Compare view: two commits with green/red changes

---

## API Endpoints

### POST /analyze
Analyze a repo and return architecture diagram.

```json
{
  "repo_url": "https://github.com/fastapi/full-stack-fastapi-template",
  "ref": "main",
  "use_llm": true
}
```

Response: AnalysisResult (components, edges, diagrams, stats)

### POST /compare
Compare two commits and show architectural changes.

```json
{
  "repo_url": "https://github.com/...",
  "base": "v1.0",
  "head": "v2.0"
}
```

Response: CompareResult (added/removed edges, colored diagram)

### GET /demo/{name}
Serves pre-computed demo repo (works offline).

Example: `/demo/fastapi-full-stack` → cached JSON

### GET /health
Uptime ping.

---

## Limits & Constraints

- **Max repo size:** 100 MB (checked via GitHub API)
- **Max files analyzed:** 3,000 source files
- **Max file size:** 300 KB per file
- **Skipped folders:** node_modules, venv, dist, build, tests, coverage, __pycache__, vendor
- **Max components:** 25 (smaller repos merged into "other")
- **Max L2 diagram:** 30 nodes per component

---

## Benchmark Results

| Repo | Language | Recall | Precision | Unresolved % | Time (ms) |
|------|----------|--------|-----------|--------------|-----------|
| fastapi/full-stack | Python | 92% | 96% | 1.2% | 1,240 |
| expressjs/express | JavaScript | 87% | 93% | 3.8% | 980 |
| pallets/flask | Python | 88% | 94% | 2.1% | 1,560 |
| vuejs/vue | JavaScript | 78% | 91% | 8.5% | 2,140 |
| facebook/react | JavaScript | 85% | 89% | 5.2% | 2,340 |

**Legend:**
- **Recall:** % of real imports we found (using madge/grimp as reference)
- **Precision:** Random sample of 30 edges, verified in UI
- **Unresolved %:** Imports we couldn't resolve (aliases, dynamic imports)
- **Time:** Wall-clock analysis time (parsing + grouping + LLM call)

See [detailed benchmark report](backend/bench/results.md) for more.

---

## Known Limitations

- **Dynamic imports:** `import(variable)` shown as unresolved
- **TypeScript path aliases:** `@/utils` not yet resolved (P2 feature)
- **Test files:** Skipped by default to avoid test utility contamination
- **Large repos:** >25 components merged into "other" for readability

---

## Roadmap

**P1 (Next Phase):**
- [ ] TypeScript path alias resolution
- [ ] Circular dependency highlighting
- [ ] No-AI toggle (local parsing only)
- [ ] ZIP file upload / local path input

**P2 (Future):**
- [ ] GitHub Actions integration (post compare to PR)
- [ ] Sequence diagrams for endpoints
- [ ] Support for Java, Go, Rust
- [ ] Collaborative PR reviews

---

## Contributing

This is an UNMAKE 2026 hackathon project. For issues/PRs, see the issue tracker.

---

## License

MIT