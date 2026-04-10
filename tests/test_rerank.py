from __future__ import annotations

import numpy as np

from app.indexing.vector_store import Document
from app.llm.rerank import CrossEncoderReranker, vector_order_top_k


def test_vector_order_top_k_trims() -> None:
    hits = [
        (0.1, Document("a", "t1", {})),
        (0.2, Document("b", "t2", {})),
        (0.3, Document("c", "t3", {})),
    ]
    out = vector_order_top_k(hits, 2)
    assert [d.doc_id for _, d in out] == ["a", "b"]


def test_cross_encoder_rerank_orders_by_model_scores() -> None:
    doc_low = Document("low", "aaa", {})
    doc_high = Document("high", "bbb", {})
    hits = [(0.9, doc_low), (0.1, doc_high)]
    reranker = CrossEncoderReranker(model_name="fake-ce")

    class FakeCE:
        def predict(self, pairs, **kwargs):
            del kwargs
            scores = []
            for q, p in pairs:
                _ = q
                if "bbb" in p:
                    scores.append(10.0)
                else:
                    scores.append(1.0)
            return np.array(scores, dtype=np.float32)

    reranker._model = FakeCE()
    out = reranker.rerank("query", hits, top_k=2)
    assert [d.doc_id for _, d in out] == ["high", "low"]


def test_cross_encoder_rerank_empty_inputs() -> None:
    reranker = CrossEncoderReranker(model_name="fake-ce")
    assert reranker.rerank("q", [], top_k=3) == []
