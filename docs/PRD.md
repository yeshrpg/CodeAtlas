\# CodeAtlas — PRD



\## 1. Product

Paste a public GitHub repo (Python/JS/TS). Get an interactive architecture diagram where every connection is a real import (expand to see file:line), AI-written labels, and a compare view between two commits.



Pitch line: "The code decides the connections. AI explains them."



Difference vs GitDiagram / DeepWiki (as far as we found): they infer architecture from the file tree, README and an LLM. We parse the real imports, show evidence, and compare commits.



\## 2. Locked decisions (never reopen)

\- ONE Gemini call per analysis. The LLM never decides edges and never writes Mermaid.

\- Folder-based grouping into 5-25 components. No clustering algorithms.

\- Python parsed with the `ast` module. JS/TS parsed with a regex extractor (tree-sitter is roadmap only).

\- No SSE, no SQLite, no CLI product, no Docker. In-memory dict cache + demo JSON files committed to the repo.

\- Every LLM or network failure has a deterministic fallback.

\- Unresolved imports go to an "unresolved" bucket. Never guess an edge.

\- Public repos only. Limits: repo size 100 MB or less (checked via API before download), 3000 source files max, files over 300 KB skipped, skip node\_modules, venv, dist, build, .git, \_\_pycache\_\_, vendor, tests.

