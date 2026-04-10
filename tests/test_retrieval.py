from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.indexing.search_filters import SearchFilterSpec
from app.indexing.vector_store import VectorStore
from app.llm.retrieval import RetrievalOptions, RetrievalPipeline, build_default_pipeline
from app.llm.rerank import CrossEncoderReranker


@pytest.fixture
def pipeline(vector_store_with_docs: VectorStore) -> RetrievalPipeline:
    settings = Settings(
        embedding_model_name="fake-mini",
        index_dir=Path("indexes/default"),
        search_top_k=5,
        retrieve_multiplier=2,
        retrieve_max_candidates=50,
        rerank_enabled=False,
    )
    rr = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    return RetrievalPipeline(store=vector_store_with_docs, settings=settings, reranker=rr)


def test_retrieve_respects_top_k(pipeline: RetrievalPipeline) -> None:
    out = pipeline.retrieve("powershell suspicious", top_k=2)
    assert len(out) <= 2


def test_filter_drops_high_event_hosts(pipeline: RetrievalPipeline) -> None:
    spec = SearchFilterSpec(max_num_events=20)
    opts = RetrievalOptions(filter_spec=spec)
    out = pipeline.retrieve("external https traffic", top_k=5, options=opts)
    for _s, d in out:
        assert int(d.metadata.get("num_events", 0)) <= 20


def test_ioc_narrow_prefers_matching_docs(pipeline: RetrievalPipeline) -> None:
    opts = RetrievalOptions(narrow_by_ioc_overlap=True)
    out = pipeline.retrieve("203.0.113.50 beacon", top_k=5, options=opts)
    texts = " ".join(d.text for _, d in out)
    assert "203.0.113.50" in texts


def test_build_default_pipeline_smoke(vector_store_with_docs: VectorStore, tmp_path: Path) -> None:
    settings = Settings(
        embedding_model_name="fake-mini",
        index_dir=tmp_path,
        search_top_k=3,
        rerank_enabled=False,
    )
    pipe = build_default_pipeline(vector_store_with_docs, settings)
    hits = pipe.retrieve("windows", top_k=2)
    assert len(hits) <= 2


def test_effective_retrieve_k_respects_cap() -> None:
    store = SimpleNamespace(_docs=list(range(1000)))
    settings = Settings(
        embedding_model_name="fake",
        index_dir=Path("."),
        search_top_k=5,
        retrieve_multiplier=100,
        retrieve_max_candidates=7,
        rerank_enabled=False,
    )
    rr = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    pipe = RetrievalPipeline(store=store, settings=settings, reranker=rr)  # type: ignore[arg-type]
    rk = pipe._effective_retrieve_k(top_k=5, override=None)
    assert rk == 7
