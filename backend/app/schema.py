"""
CodeAtlas — Pydantic v2 data models.

Source of truth: docs/schema.md. Every model here must match that doc
exactly. If a future change is needed, update docs/schema.md FIRST, then
this file, in the same commit.

Locked constraints reflected here:
- Folder-based grouping only, 5-25 components.
- Unresolved imports go into an explicit "unresolved" bucket, never guessed.
- LLM produces labels/summaries only — never edges, never Mermaid syntax.
- All paths are stored as POSIX strings (.as_posix()) — never backslashes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Language(str, Enum):
    python = "python"
    javascript = "javascript"
    typescript = "typescript"
    other = "other"


class ImportResolutionStatus(str, Enum):
    resolved = "resolved"
    unresolved = "unresolved"
    external = "external"  # resolved to a third-party package, not a repo file


class AnalysisStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class LabelSource(str, Enum):
    llm = "llm"
    heuristic = "heuristic"  # deterministic fallback when LLM step is skipped/fails


# ---------------------------------------------------------------------------
# Path helpers — every model holding a repo-relative path validates it to
# POSIX form so Windows dev machines can never leak backslashes into output.
# ---------------------------------------------------------------------------

def _to_posix(v: str) -> str:
    return v.replace("\\", "/")


# ---------------------------------------------------------------------------
# Import / symbol level
# ---------------------------------------------------------------------------

class ImportRef(BaseModel):
    """A single import statement found in a parsed file, plus its resolution."""

    raw: str = Field(..., description="Import statement exactly as written in source")
    module: str = Field(..., description="Dotted/module or package name being imported")
    line: int = Field(..., ge=1, description="1-indexed line number of the import statement")
    status: ImportResolutionStatus
    resolved_path: Optional[str] = Field(
        default=None, description="POSIX repo-relative path if status == resolved"
    )

    @field_validator("resolved_path")
    @classmethod
    def _posix_resolved_path(cls, v: Optional[str]) -> Optional[str]:
        return _to_posix(v) if v else v

    @field_validator("resolved_path")
    @classmethod
    def _require_resolved_path_when_resolved(cls, v, info):
        status = info.data.get("status")
        if status == ImportResolutionStatus.resolved and not v:
            raise ValueError("resolved_path is required when status == 'resolved'")
        return v


class SymbolRef(BaseModel):
    """A top-level function/class/route symbol discovered during parsing."""

    name: str
    kind: Literal["function", "class", "route", "variable"]
    line: int = Field(..., ge=1)
    docstring: Optional[str] = None
    route_path: Optional[str] = Field(
        default=None, description="Set only when kind == 'route' (e.g. FastAPI/Flask decorator path)"
    )
    route_methods: list[str] = Field(default_factory=list)


class ParsedFile(BaseModel):
    """Result of parsing a single source file (Python via `ast`, JS/TS via regex extractor)."""

    path: str = Field(..., description="POSIX repo-relative file path")
    language: Language
    line_count: int = Field(..., ge=0)
    docstring: Optional[str] = None
    imports: list[ImportRef] = Field(default_factory=list)
    symbols: list[SymbolRef] = Field(default_factory=list)
    parse_error: Optional[str] = Field(
        default=None, description="Set when the file could not be parsed; imports/symbols will be empty"
    )

    @field_validator("path")
    @classmethod
    def _posix_path(cls, v: str) -> str:
        return _to_posix(v)


# ---------------------------------------------------------------------------
# Grouping / component level
# ---------------------------------------------------------------------------

class ComponentLabel(BaseModel):
    """Human-readable label + one-line summary for a component, plus provenance."""

    name: str
    summary: str
    source: LabelSource


class Component(BaseModel):
    """One folder-derived component/group node in the final architecture graph."""

    id: str = Field(..., description="Stable slug id, unique within the analysis")
    folder_path: str = Field(..., description="POSIX repo-relative folder path this component represents")
    files: list[str] = Field(default_factory=list, description="POSIX paths of files in this component")
    label: ComponentLabel
    is_other_merge: bool = Field(
        default=False, description="True if this is the catch-all 'other' bucket from the merge guard"
    )

    @field_validator("folder_path")
    @classmethod
    def _posix_folder(cls, v: str) -> str:
        return _to_posix(v)

    @field_validator("files")
    @classmethod
    def _posix_files(cls, v: list[str]) -> list[str]:
        return [_to_posix(p) for p in v]


class ComponentEdge(BaseModel):
    """A directed dependency edge between two components, derived from resolved imports."""

    source_id: str
    target_id: str
    import_count: int = Field(..., ge=1, description="Number of resolved imports backing this edge")
    evidence: list[str] = Field(
        default_factory=list,
        description="file:line strings (POSIX paths) supporting this edge, for UI drill-down",
    )


class UnresolvedBucket(BaseModel):
    """Explicit bucket for imports that could not be resolved to a repo file or known package."""

    imports: list[ImportRef] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mermaid output — generated deterministically by our own code, never by the LLM
# ---------------------------------------------------------------------------

class MermaidOutput(BaseModel):
    diagram_type: Literal["graph TD", "graph LR"] = "graph TD"
    source: str = Field(..., description="Full Mermaid diagram source, generated deterministically")


# ---------------------------------------------------------------------------
# Repo / analysis metadata
# ---------------------------------------------------------------------------

class RepoMeta(BaseModel):
    owner: str
    name: str
    default_branch: str
    commit_sha: str
    is_public: bool
    total_files_scanned: int = Field(..., ge=0)
    total_files_skipped: int = Field(..., ge=0)
    total_size_bytes: int = Field(..., ge=0)
    is_flat_repo: bool = Field(
        default=False, description="True if the flat-repo (top-25-files) guard was triggered"
    )


class AnalysisResult(BaseModel):
    """Top-level response for a single repo analysis."""

    analysis_id: str
    status: AnalysisStatus
    repo: RepoMeta
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    

    parsed_files: list[ParsedFile] = Field(default_factory=list)
    components: list[Component] = Field(
        default_factory=list, description="5-25 folder-based components"
    )
    edges: list[ComponentEdge] = Field(default_factory=list)
    unresolved: UnresolvedBucket = Field(default_factory=UnresolvedBucket)
    mermaid: Optional[MermaidOutput] = None
    health: Optional[dict] = None

    llm_model: Optional[str] = Field(
        default=None, description="Value of GEMINI_MODEL used for this analysis, if the LLM step ran"
    )
    llm_call_count: int = Field(default=0, ge=0, le=1, description="Locked to at most one LLM call per analysis")

    @field_validator("components")
    @classmethod
    def _component_count_bounds(cls, v: list[Component]) -> list[Component]:
        if v and not (5 <= len(v) <= 25):
            raise ValueError("components must number between 5 and 25 when non-empty")
        return v


# ---------------------------------------------------------------------------
# Compare (P1 / stretch — Y8)
# ---------------------------------------------------------------------------

class ComponentDiff(BaseModel):
    id: str
    folder_path: str
    change: Literal["added", "removed", "modified", "unchanged"]
    detail: Optional[str] = None


class EdgeDiff(BaseModel):
    source_id: str
    target_id: str
    change: Literal["added", "removed", "unchanged"]


class CompareResult(BaseModel):
    """Diff between two AnalysisResult objects for the same repo (or two repos)."""

    compare_id: str
    base_analysis_id: str
    head_analysis_id: str
    created_at: datetime
    component_diffs: list[ComponentDiff] = Field(default_factory=list)
    edge_diffs: list[EdgeDiff] = Field(default_factory=list)
    summary: Optional[str] = None
