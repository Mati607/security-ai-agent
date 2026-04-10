from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.config import Settings
from app.indexing.search_filters import (
    SearchFilterSpec,
    filter_hits,
    filter_hits_by_ioc_overlap,
)
from app.indexing.vector_store import Document, VectorStore
from app.llm.rerank import CrossEncoderReranker, vector_order_top_k

logger = logging.getLogger(__name__)


@dataclass
class RetrievalOptions:
    """Per-request overrides for the retrieval stack."""

    retrieve_k: Optional[int] = None
    filter_spec: Optional[SearchFilterSpec] = None
    use_rerank: Optional[bool] = None
    narrow_by_ioc_overlap: bool = False


class RetrievalPipeline:
    """Orchestrate wide FAISS retrieval, metadata filters, IOC overlap, and reranking."""

    def __init__(
        self,
        store: VectorStore,
        settings: Settings,
        reranker: CrossEncoderReranker,
    ) -> None:
        self.store = store
        self.settings = settings
        self.reranker = reranker

    def _effective_retrieve_k(self, top_k: int, override: Optional[int]) -> int:
        if override is not None:
            return max(top_k, override)
        mult = max(1, self.settings.retrieve_multiplier)
        cap = self.settings.retrieve_max_candidates
        raw = top_k * mult
        if cap > 0:
            raw = min(raw, cap)
        n_docs = len(self.store._docs)
        if n_docs == 0:
            return top_k
        return min(max(raw, top_k), n_docs)

    def _should_rerank(self, override: Optional[bool]) -> bool:
        if override is not None:
            return override
        return self.settings.rerank_enabled

    def retrieve(
        self,
        query: str,
        top_k: int,
        options: Optional[RetrievalOptions] = None,
    ) -> List[Tuple[float, Document]]:
        opts = options or RetrievalOptions()
        if not self.store._docs:
            return []

        rk = self._effective_retrieve_k(top_k, opts.retrieve_k)
        hits = self.store.search_candidates(query, rk)
        hits = filter_hits(hits, opts.filter_spec)

        if opts.narrow_by_ioc_overlap:
            before = len(hits)
            hits = filter_hits_by_ioc_overlap(hits, query)
            logger.debug(
                "IOC overlap narrowed candidates: %s -> %s",
                before,
                len(hits),
            )

        if not hits:
            return []

        do_rerank = self._should_rerank(opts.use_rerank)
        if do_rerank:
            return self.reranker.rerank(query, hits, top_k=top_k)

        return vector_order_top_k(hits, top_k)

    def passages(self, query: str, top_k: int, options: Optional[RetrievalOptions] = None) -> List[str]:
        return [d.text for _, d in self.retrieve(query, top_k, options)]


def build_default_pipeline(store: VectorStore, settings: Settings) -> RetrievalPipeline:
    rr = CrossEncoderReranker(model_name=settings.rerank_model_name)
    return RetrievalPipeline(store=store, settings=settings, reranker=rr)
