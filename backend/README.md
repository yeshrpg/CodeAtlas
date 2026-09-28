# CodeAtlas Backend

Parse GitHub repositories and generate interactive architecture diagrams.

## Quick Start

\\\ash
cd backend
python -m uvicorn app.main:app --reload --port 8000
\\\

Server running at \http://localhost:8000\

## API Endpoints

### POST /analyze
Analyze a repository and extract architecture.

**Request:**
\\\json
{
  "repo_url": "https://github.com/fastapi/full-stack-fastapi-template",
  "ref": "main",
  "use_llm": true
}
\\\

**Response:**
\\\json
{
  "repo": "https://...",
  "commit_sha": "abc123",
  "stats": {
    "files": 0,
    "edges": 0,
    "ms": 0
  },
  "components": [],
  "edges": []
}
\\\

### GET /health
Health check endpoint.

**Response:** \{"status": "ok"}\

### GET /
Root endpoint.

**Response:** \{"message": "CodeAtlas API", "docs": "/docs"}\

## Architecture

\\\
backend/
├── core/              # JS/TS Parser
├── llm/               # Fallback labels
├── app/               # FastAPI app
├── bench/             # Benchmarking
├── demo_data/         # Demo JSONs
├── README.md          # This file
└── NEXT_STEPS.md      # Next steps guide
\\\

## Features

✅ JavaScript/TypeScript parser (8 tests)
✅ Automatic component labeling (5 tests)
✅ FastAPI backend with CORS
✅ Demo data for 3 repositories
✅ Measurement scripts ready
✅ Error handling

## Development

### Run Tests
\\\ash
pytest . -v
\\\

### Install Dependencies
\\\ash
pip install fastapi uvicorn pydantic requests pytest
\\\

### File Structure
- \pp/main.py\ - FastAPI application
- \core/parse_js.py\ - JS/TS parser
- \llm/fallback.py\ - Heuristic labels
- \ench/measure_precision_recall.py\ - Measurement script
- \demo_data/*.json\ - Example outputs

## Status

✅ Backend running on http://localhost:8000
✅ All 14 tests passing
✅ API endpoints functional
✅ Ready for parser integration

## Next Steps

See \NEXT_STEPS.md\ for integration workflow.
