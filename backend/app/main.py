"""CodeAtlas Backend API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="CodeAtlas")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str
    ref: str = "main"
    use_llm: bool = True


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    """Placeholder for /analyze endpoint."""
    return {
        "repo": request.repo_url,
        "ref": request.ref,
        "commit_sha": "abc123",
        "stats": {
            "files": 0,
            "skipped": 0,
            "edges": 0,
            "unresolved_pct": 0.0,
            "ms": 0,
            "llm_used": request.use_llm
        },
        "components": [],
        "edges": [],
        "files": [],
        "diagrams": {"l1": {"mermaid": "", "node_map": {}}, "l2": {}},
        "onboarding": {"summary": "", "reading_order": []}
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "CodeAtlas API"}