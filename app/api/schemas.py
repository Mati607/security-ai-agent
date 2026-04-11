from __future__ import annotations

from pydantic import BaseModel, Field

from app.indexing.search_filters import filter_spec_from_mapping
from app.llm.retrieval import RetrievalOptions


class SearchFiltersBody(BaseModel):
    """Post-retrieval constraints applied after widening FAISS `retrieve_k`."""

    min_vector_score: float | None = None
    min_num_events: int | None = Field(default=None, ge=0)
    max_num_events: int | None = Field(default=None, ge=0)
    group_key_contains: str | None = None
    doc_id_contains: str | None = None
    metadata_equals: dict[str, str] = Field(default_factory=dict)
    metadata_contains: dict[str, str] = Field(default_factory=dict)
    timestamp_after: str | None = None
    timestamp_before: str | None = None
    require_timestamp: bool = False


class RetrievalControls(BaseModel):
    retrieve_k: int | None = Field(default=None, ge=1)
    filters: SearchFiltersBody | None = None
    use_rerank: bool | None = None
    narrow_by_ioc_overlap: bool = False


class SearchRequest(RetrievalControls):
    query: str
    top_k: int | None = Field(default=None, ge=1)


class SearchResult(BaseModel):
    score: float
    doc_id: str
    text: str
    metadata: dict


class ContextRequest(RetrievalControls):
    alert: str
    top_k: int | None = Field(default=None, ge=1)


class TriageRequest(RetrievalControls):
    alert: str
    top_k: int | None = Field(default=None, ge=1)


def options_from_controls(ctrl: RetrievalControls) -> RetrievalOptions:
    spec = None
    if ctrl.filters is not None:
        data = ctrl.filters.model_dump(exclude_none=True)
        if data:
            spec = filter_spec_from_mapping(data)
    return RetrievalOptions(
        retrieve_k=ctrl.retrieve_k,
        filter_spec=spec,
        use_rerank=ctrl.use_rerank,
        narrow_by_ioc_overlap=ctrl.narrow_by_ioc_overlap,
    )


__all__ = [
    "ContextRequest",
    "RetrievalControls",
    "SearchFiltersBody",
    "SearchRequest",
    "SearchResult",
    "TriageRequest",
    "options_from_controls",
]
