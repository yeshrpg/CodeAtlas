# CodeAtlas Backend

Parse GitHub repositories and generate interactive architecture diagrams.

## Quick Start

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Server running at `http://localhost:8000`

## API Endpoints

### POST /analyze
Analyze a repository and extract architecture.

**Request:**
```json
{
  "repo_url": "https://github.com/fastapi/full-stack-fastapi-template",
  "ref": "main",
  "use_llm": true
}
```

**Response:**
```json
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
```

### GET /health
Health check endpoint.

**Response:** `{"status": "ok"}`

### GET /
Root endpoint.

**Response:** `{"message": "CodeAtlas API", "docs": "/docs"}`

## Architecture