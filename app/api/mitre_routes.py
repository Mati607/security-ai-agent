from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.schemas import ContextRequest, options_from_controls
from app.config import Settings
from app.llm.retrieval import RetrievalPipeline
from app.mitre.mapper import get_default_mapper
from app.mitre.models import MitreMapOptions, MitreMapResult
from app.mitre.tactics import all_tactics
from app.mitre.techniques_catalog import TECHNIQUES


class MitreCatalogResponse(BaseModel):
    """Bundled tactic list plus catalogue size for UI clients."""

    tactics: List[dict] = Field(default_factory=list)
    technique_count: int = 0
    note: str = Field(
        default="Keyword heuristic over a subset of Enterprise ATT&CK; not an official MITRE mapping.",
    )


class MitreMapRequest(BaseModel):
    """Map arbitrary SOC text to likely techniques."""

    text: str = Field(..., min_length=1, max_length=200_000)
    top_n: int | None = Field(default=None, ge=1, le=64)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    max_keyword_hits_per_term: int | None = Field(default=None, ge=1, le=32)


def mitre_options_from_request(body: MitreMapRequest, settings: Settings) -> MitreMapOptions:
    """Apply request overrides on top of configured defaults."""

    return MitreMapOptions(
        top_n=body.top_n if body.top_n is not None else settings.mitre_map_top_n,
        min_confidence=body.min_confidence
        if body.min_confidence is not None
        else settings.mitre_map_min_confidence,
        max_keyword_hits_per_term=body.max_keyword_hits_per_term
        if body.max_keyword_hits_per_term is not None
        else settings.mitre_map_max_keyword_hits_per_term,
    )


class MitreContextMapResponse(BaseModel):
    """Mapping result plus a compact view of passages used as extra context."""

    mitre: MitreMapResult
    num_context_docs: int
    context_doc_ids: List[str] = Field(default_factory=list)


def create_mitre_router(pipeline: RetrievalPipeline, settings: Settings) -> APIRouter:
    router = APIRouter()
    mapper = get_default_mapper()

    @router.get("/catalog", response_model=MitreCatalogResponse)
    def get_catalog() -> MitreCatalogResponse:
        tactics = [{"id": t.id, "name": t.name, "url": t.url} for t in all_tactics()]
        return MitreCatalogResponse(tactics=tactics, technique_count=len(TECHNIQUES))

    @router.post("/map", response_model=MitreMapResult)
    def map_free_text(body: MitreMapRequest) -> MitreMapResult:
        opts = mitre_options_from_request(body, settings)
        return mapper.map_text(body.text, options=opts)

    @router.post("/map-with-context", response_model=MitreContextMapResponse)
    def map_with_retrieval(body: ContextRequest) -> MitreContextMapResponse:
        top_k = body.top_k or settings.search_top_k
        opts_ret = options_from_controls(body)
        hits = pipeline.retrieve(body.alert, top_k=top_k, options=opts_ret)
        passages = [doc.text for _, doc in hits]
        map_opts = MitreMapOptions(
            top_n=settings.mitre_map_top_n,
            min_confidence=settings.mitre_map_min_confidence,
            max_keyword_hits_per_term=settings.mitre_map_max_keyword_hits_per_term,
        )
        mitre_out = mapper.map_alert_with_hits(body.alert, passages, options=map_opts)
        doc_ids = [doc.doc_id for _, doc in hits]
        return MitreContextMapResponse(
            mitre=mitre_out,
            num_context_docs=len(hits),
            context_doc_ids=doc_ids,
        )

    return router
