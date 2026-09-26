\# CodeAtlas — API Spec



\- `POST /analyze` `{repo\_url, ref?, use\_llm=true}` returns `AnalysisResult`

\- `POST /compare` `{repo\_url, base, head}` returns `CompareResult` (P1)

\- `GET /demo/{name}` returns a committed JSON file

\- `GET /health` returns `{"ok": true}`

