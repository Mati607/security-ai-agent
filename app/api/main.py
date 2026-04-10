from __future__ import annotations

from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.indexing.search_filters import filter_spec_from_mapping
from app.indexing.vector_store import VectorStore
from app.llm.contextualize import AlertContextualizer
from app.llm.retrieval import RetrievalOptions, build_default_pipeline


app = FastAPI(title="AI-Driven SOC API")
settings = get_settings()
_store = VectorStore.load(model_name=settings.embedding_model_name, index_dir=settings.index_dir)
_pipeline = build_default_pipeline(_store, settings)
_contextualizer = AlertContextualizer(model_name=settings.summarizer_model_name)


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


def _options_from_controls(ctrl: RetrievalControls) -> RetrievalOptions:
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


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


@app.post("/search", response_model=List[SearchResult])
def search(body: SearchRequest) -> List[SearchResult]:
    top_k = body.top_k or settings.search_top_k
    opts = _options_from_controls(body)
    results = _pipeline.retrieve(body.query, top_k=top_k, options=opts)
    payload: List[SearchResult] = []
    for score, doc in results:
        payload.append(
            SearchResult(score=score, doc_id=doc.doc_id, text=doc.text, metadata=doc.metadata)
        )
    return payload


@app.post("/search/advanced", response_model=List[SearchResult])
def search_advanced(body: SearchRequest) -> List[SearchResult]:
    """Explicit alias for clients that want the extended retrieval contract."""

    return search(body)


@app.post("/contextualize")
def contextualize(body: ContextRequest) -> dict:
    top_k = body.top_k or settings.search_top_k
    opts = _options_from_controls(body)
    results = _pipeline.retrieve(body.alert, top_k=top_k, options=opts)
    passages = [doc.text for _, doc in results]
    brief = _contextualizer.summarize(body.alert, passages)
    return {
        "brief": brief,
        "num_context": len(passages),
        "rerank": opts.use_rerank if opts.use_rerank is not None else settings.rerank_enabled,
    }


@app.post("/triage")
def triage(body: TriageRequest) -> dict:
    top_k = body.top_k or settings.search_top_k
    opts = _options_from_controls(body)
    results = _pipeline.retrieve(body.alert, top_k=top_k, options=opts)
    passages = [doc.text for _, doc in results]
    brief = _contextualizer.summarize(body.alert, passages)
    payload = [
        {"score": float(score), "doc_id": doc.doc_id, "metadata": doc.metadata}
        for score, doc in results
    ]
    return {
        "alert": body.alert,
        "brief": brief,
        "search_results": payload,
        "rerank": opts.use_rerank if opts.use_rerank is not None else settings.rerank_enabled,
    }
