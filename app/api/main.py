from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI

from app.api.auth_routes import create_auth_router
from app.api.cases_routes import create_cases_router
from app.api.mitre_routes import create_mitre_router
from app.auth.deps import build_get_current_user
from app.api.schemas import (
    ContextRequest,
    IndexInfo,
    SearchRequest,
    SearchResult,
    TriageRequest,
    options_from_controls,
)
from app.cases.service import CaseInvestigationService
from app.cases.store import CaseStore
from app.config import get_settings
from app.indexing.vector_store import VectorStore
from app.llm.contextualize import AlertContextualizer
from app.llm.retrieval import build_default_pipeline

settings = get_settings()
_store = VectorStore.load(model_name=settings.embedding_model_name, index_dir=settings.index_dir)
_pipeline = build_default_pipeline(_store, settings)
_contextualizer = AlertContextualizer(model_name=settings.summarizer_model_name)

_case_store = CaseStore(settings.cases_db_path)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Initialize SQLite schema on the active case store (supports test overrides)."""

    _case_store.init_db()
    yield


app = FastAPI(title="AI-Driven SOC API", lifespan=_lifespan)
_case_service = CaseInvestigationService(
    _case_store,
    _pipeline,
    _contextualizer,
    settings,
)
_get_current_user = build_get_current_user(lambda: _case_store, settings)
app.include_router(
    create_auth_router(lambda: _case_store, settings, _get_current_user),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    create_cases_router(lambda: _case_store, lambda: _case_service, settings, _get_current_user),
    prefix="/cases",
    tags=["cases"],
)
app.include_router(
    create_mitre_router(_pipeline, settings),
    prefix="/mitre",
    tags=["mitre"],
)


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


@app.get("/index/info", response_model=IndexInfo)
def index_info() -> IndexInfo:
    """Return vector index metadata (counts, paths, embedding model)."""

    return IndexInfo(**_store.index_info())


@app.post("/search", response_model=List[SearchResult])
def search(body: SearchRequest) -> List[SearchResult]:
    top_k = body.top_k or settings.search_top_k
    opts = options_from_controls(body)
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
    opts = options_from_controls(body)
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
    opts = options_from_controls(body)
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
