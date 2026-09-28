from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class Language(str, Enum):
    python = "python"
    javascript = "javascript"
    typescript = "typescript"
    other = "other"

class ImportResolutionStatus(str, Enum):
    resolved = "resolved"
    unresolved = "unresolved"
    external = "external"

class AnalysisStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"

class LabelSource(str, Enum):
    llm = "llm"
    heuristic = "heuristic"

def _to_posix(v: str) -> str:
    return v.replace("\\", "/")

class ImportRef(BaseModel):
    raw: str
    module: str
    line: int
    status: ImportResolutionStatus
    resolved_path: Optional[str] = None

class SymbolRef(BaseModel):
    name: str
    kind: Literal["function", "class", "route", "variable"]
    line: int
    docstring: Optional[str] = None
    route_path: Optional[str] = None
    route_methods: list[str] = Field(default_factory=list)

class ParsedFile(BaseModel):
    path: str
    language: Language
    line_count: int
    docstring: Optional[str] = None
    imports: list[ImportRef] = Field(default_factory=list)
    symbols: list[SymbolRef] = Field(default_factory=list)
    parse_error: Optional[str] = None

class ComponentLabel(BaseModel):
    name: str
    summary: str
    source: LabelSource

class Component(BaseModel):
    id: str
    folder_path: str
    files: list[str] = Field(default_factory=list)
    label: ComponentLabel
    is_other_merge: bool = False

class ComponentEdge(BaseModel):
    source_id: str
    target_id: str
    import_count: int
    evidence: list[str] = Field(default_factory=list)

class UnresolvedBucket(BaseModel):
    imports: list[ImportRef] = Field(default_factory=list)

class MermaidOutput(BaseModel):
    diagram_type: Literal["graph TD", "graph LR"] = "graph TD"
    source: str

class RepoMeta(BaseModel):
    owner: str
    name: str
    default_branch: str
    commit_sha: str
    is_public: bool
    total_files_scanned: int
    total_files_skipped: int
    total_size_bytes: int
    is_flat_repo: bool = False

class AnalysisResult(BaseModel):
    analysis_id: str
    status: AnalysisStatus
    repo: RepoMeta
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    parsed_files: list[ParsedFile] = Field(default_factory=list)
    components: list[Component] = Field(default_factory=list)
    edges: list[ComponentEdge] = Field(default_factory=list)
    unresolved: UnresolvedBucket = Field(default_factory=UnresolvedBucket)
    mermaid: Optional[MermaidOutput] = None
    llm_model: Optional[str] = None
    llm_call_count: int = 0

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
    compare_id: str
    base_analysis_id: str
    head_analysis_id: str
    created_at: datetime
    component_diffs: list[ComponentDiff] = Field(default_factory=list)
    edge_diffs: list[EdgeDiff] = Field(default_factory=list)
    summary: Optional[str] = None