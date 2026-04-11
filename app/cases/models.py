from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.cases.constants import CaseSeverity, CaseStatus, TimelineKind


class CaseCreate(BaseModel):
    """Payload to open a new investigation case."""

    title: str = Field(..., min_length=1, max_length=512)
    status: CaseStatus = CaseStatus.OPEN
    severity: Optional[CaseSeverity] = None
    owner: Optional[str] = Field(default=None, max_length=256)
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = Field(default=None, max_length=16_384)
    external_refs: Dict[str, str] = Field(default_factory=dict)

    @field_validator("tags", mode="before")
    @classmethod
    def _strip_tags(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


class CaseUpdate(BaseModel):
    """Partial update for case metadata (all fields optional)."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    status: Optional[CaseStatus] = None
    severity: Optional[CaseSeverity] = None
    owner: Optional[str] = Field(default=None, max_length=256)
    tags: Optional[List[str]] = None
    summary: Optional[str] = Field(default=None, max_length=16_384)
    external_refs: Optional[Dict[str, str]] = None

    @field_validator("tags", mode="before")
    @classmethod
    def _strip_tags(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return v


class CaseSummary(BaseModel):
    """List view row for a case."""

    id: str
    title: str
    status: CaseStatus
    severity: Optional[CaseSeverity] = None
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    timeline_count: int = 0


class TimelineEntry(BaseModel):
    """Single timeline row (note, snapshot, or system event)."""

    id: int
    case_id: str
    kind: TimelineKind
    title: Optional[str] = None
    body: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: str


class CaseDetail(BaseModel):
    """Full case with timeline for detail and export views."""

    id: str
    title: str
    status: CaseStatus
    severity: Optional[CaseSeverity] = None
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    external_refs: Dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    timeline: List[TimelineEntry] = Field(default_factory=list)


class NoteCreate(BaseModel):
    """Analyst note appended to the timeline."""

    title: Optional[str] = Field(default=None, max_length=512)
    body: str = Field(..., min_length=1, max_length=65_536)


class SearchSnapshotCreate(BaseModel):
    """Persist a vector search result set under a case."""

    query: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=10, ge=1, le=200)
    results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Each item typically includes score, doc_id, text, metadata",
    )


class TriageSnapshotPayload(BaseModel):
    """Structured payload stored for a triage timeline entry."""

    alert: str
    brief: str
    rerank: bool
    search_results: List[Dict[str, Any]]


class CaseListParams(BaseModel):
    """Query parameters for listing cases."""

    status: Optional[CaseStatus] = None
    owner: Optional[str] = None
    title_contains: Optional[str] = Field(default=None, max_length=256)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class IOCAggregate(BaseModel):
    """IOC-shaped tokens aggregated from case text for quick analyst view."""

    ipv4: List[str] = Field(default_factory=list)
    sha256: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
