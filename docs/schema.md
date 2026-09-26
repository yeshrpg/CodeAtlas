\# CodeAtlas — Schema



\## JSON contract (Pydantic v2 in backend/app/schema.py)



\*\*AnalysisResult:\*\*

\- `repo`, `ref`, `commit\_sha`

\- `stats`: `{files, skipped, edges, unresolved\_pct, ms, llm\_used}`

\- `components\[]`: `{id, node\_id, label, layer, summary, files\[], in\_deg, out\_deg, label\_source: "llm"|"heuristic"}`

\- `edges\[]`: `{src, dst, weight, evidence\[]: {file, line, stmt}}` (component level, evidence capped at 20)

\- `file\_edges\[]`: `{src, dst, line, stmt}`

\- `files\[]`: `{path, component, symbols\[], imports\[], unresolved\[]}`

\- `diagrams`: `{l1: {mermaid, node\_map: {n1: component\_id}}, l2: {component\_id: {mermaid, node\_map: {f1: file\_path, x1: neighbor\_component\_id}}}}`

\- `onboarding`: `{summary, reading\_order\[]: {path, reason, source}}`



\*\*CompareResult:\*\* `{base, head, added\_edges\[], removed\_edges\[], added\_components\[], removed\_components\[], diagram: {mermaid, node\_map}}`



\*\*ImportRef\*\* (shared by both parsers): `{spec: str, level: int, names: \[str], line: int, stmt: str}`



\*\*ParsedFile:\*\* `{path, lang, symbols\[], imports\[ImportRef], routes\[], doc\_first\_line, libs\[]}`



\## LLM contract

Input: `components \[{id, n\_files, symbols<=6, docs<=2 (120 chars each), imports\_from\[], imported\_by\[], libs<=6, routes<=3}]` + `reading\_candidates` (5 file paths chosen by code). Never full source. Budget about 3,500 input tokens.



Output JSON: `{repo\_summary (max 60 words), components: \[{id, label (max 3 words), layer (api|service|data|model|util|ui|config|external|other), summary (max 20 words)}], reading\_order: \[{path, reason (max 12 words)}]}`.



Call settings: `response\_mime\_type application/json` with a Pydantic `response\_schema`, thinking level low, temperature left at default, 15s timeout.



Validation: ids must match exactly, unknown ids dropped, missing ones filled from fallback, paths must exist, labels sanitized. Invalid JSON: retry once. 429: wait once only if retry-after is 8s or less. Otherwise use heuristic labels and show a "labels: heuristic" badge.

