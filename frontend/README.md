# CodeAtlas — Frontend

CodeAtlas is a code-to-architecture diagram visualizer (hackathon project): point it
at a repository and it renders the codebase as an interactive component diagram.
This directory (`frontend/`) is the web UI. The backend (analysis API, deployed
separately) produces `analysis` JSON objects; this app renders them as Mermaid
diagrams with drill-down detail panels, and can also run fully offline against the
mock data in `src/mock/`.

## Tech stack

- React 19 + TypeScript (~6.0) + Vite 8 (see `package.json`)
- `mermaid` v12 for diagram rendering (SVG output only — no `click` directives)
- Plain CSS (`src/index.css` variables + `src/App.css`) — no Tailwind, no UI kit
- No router, no state management library, no pan-zoom library
- `oxlint` for linting (`npm run lint`)

## Run locally

```sh
cd frontend
npm install
npm run dev        # serves on http://localhost:5173
```

The app needs `frontend/.env.local` (gitignored, not committed):

```
VITE_API_URL=http://localhost:8000
```

Only `VITE_`-prefixed vars reach the browser. The only client-side env var is
`VITE_API_URL`, read in `src/components/DemoDropdown.tsx` and
`src/components/CompareView.tsx` (both with a localhost fallback). No backend
secrets belong in this directory.

Other scripts: `npm run build` (`tsc -b && vite build`), `npm run preview`,
`npm run lint`.

## Structure

```
frontend/
  index.html                     Vite entry, mounts /src/main.tsx
  vite.config.ts                 stock Vite + React plugin config
  .env.local                     VITE_API_URL (local only, gitignored)
  src/
    main.tsx                     React entry point, renders <App/>
    App.tsx                      Analyze/Compare tab switcher; holds all
                                 Analyze-view state (analysis, loading, error,
                                 selection, L1/L2)
    App.css / index.css          all styling (plain CSS, light/dark aware)
    types.ts                     Analysis + Compare types (backend contract)
    mock/
      analysis.json              mock /analyze response (3 components, 2 edges)
      compare.json               mock /compare response (with diff + reading order)
    assets/                      unused Vite-template images (unreferenced)
    components/
      Header.tsx                 title, repo URL + ref inputs, Analyze button
      StatsBar.tsx               stats chips + "labels: heuristic" badge
      DemoDropdown.tsx           demo repos, GET ${VITE_API_URL}/demo/{name}
      ErrorBanner.tsx            dismissible error banner
      DiagramView.tsx            Mermaid init/render, fallback table, node clicks,
                                 export bar wiring
      SidePanel.tsx              component view <-> file view details panel
      ConnectionsList.tsx        incoming/outgoing connections + evidence
      ConnectionsTable.tsx       full From/To/Weight table under the diagram
      ExportControls.tsx         Copy Mermaid + Download SVG buttons
      CompareView.tsx            base/head inputs, POST /compare, diff lists,
                                 reading order (reuses DiagramView + SidePanel)
    lib/
      toMermaid.ts               pure analysis -> Mermaid flowchart string;
                                 stable node ids via toNodeId()
      nodeMapping.ts             maps rendered g.node DOM ids back to component
                                 ids; attaches/cleans up click listeners
      subgraph.ts                pure full-analysis -> L2 subset for one component
      exportDiagram.ts           clipboard + SVG Blob download helpers
```

## Data contract (for backend integration)

The backend must produce the `Analysis` shape defined in `src/types.ts`:

- `components[]`: `{ id, label, layer, summary, label_source: "heuristic"|"llm",
  files: string[], file_details?: Record<path, { symbols[], imports[]: {name, line, from?},
  importers[] }> }`
- `connections[]`: `{ from, to, weight, evidence?: [{ file, line, text }] }`
- `stats`: `{ files, skipped, edges, unresolved_pct, ms }`

`file_details` and `evidence` are optional — the UI renders "none" when absent.
The compare endpoint must return `CompareResponse`: `{ analysis, added_components[],
removed_components[], added_connections[], removed_connections[],
reading_order?: string[] }` (reading order = ordered component ids).
Endpoints the UI calls: `GET /demo/{name}`, `POST /compare` (`{base:{repo_url,ref?},
head:{repo_url,ref?}}`), and (for deploy verification) `GET /health`.

## Features by stage (all in git log)

- A1 `chore: scaffold frontend` — Vite+React+TS app, mock data, mermaid dep, `.env.local`
- A2 `feat: add app layout shell…` — header, spinner, error banner, stats, demo dropdown
- A3 `feat: render Mermaid diagram…` — strict/neutral Mermaid init, `toMermaid`, SVG
  render, fallback table, scrollable container
- A4 `feat: make diagram nodes clickable…` — DOM-id mapping (`<renderId>-flowchart-
  <nodeId>-<index>`, verified against mermaid 12.0.0), listeners re-attached per render
- A5 `feat: add side panel…` — component/file views, evidence lists, connections
  table, L2 detail diagram + Back
- A6 `feat: add copy-Mermaid and download-SVG…` — clipboard + Blob export, L1/L2 aware
- A7 deploy prep only (not deployed): build verified, imports case-clean, no secrets
- P1 `feat: add compare tab` — Compare view with mock-data button, green/red diffs,
  reading order
- Cleanup `chore: remove node-click debug log` — removed A4 `console.log`

## Known intentional stubs (not bugs)

- The Analyze button feeds mock `analysis.json` after a 500ms simulated delay —
  no real `/analyze` call exists yet (`src/App.tsx`).
- The demo list is 3 hardcoded names; with no backend running, selecting one shows
  the error banner — expected until the backend exists.
- The Compare tab's "Use mock data" button loads `compare.json` for the same reason.
- `src/assets/` images are unused template leftovers.

## Left before real backend integration

1. Backend must implement `GET /demo/{name}`, `POST /compare`, and `GET /health`
   matching the contract above.
2. Point the UI at it via `VITE_API_URL` (and redeploy — env changes need a rebuild).
3. Deploy this directory on Vercel with root directory `frontend`.
4. Verify the live site reaches `${VITE_API_URL}/health`; a CORS failure means the
   Vercel URL must be added to the backend's `ALLOWED_ORIGINS` (Render side, not here).
