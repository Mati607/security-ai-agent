from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.indexing.vector_store import Document, VectorStore
from tests.conftest import _FakeSentenceTransformer


def test_save_load_roundtrip(tmp_path: Path) -> None:
    docs = [
        Document(doc_id="a", text="alpha", metadata={"n": 1}),
        Document(doc_id="b", text="beta bravo", metadata={"n": 2}),
    ]
    idx = tmp_path / "vs"
    with patch("app.indexing.vector_store.SentenceTransformer", _FakeSentenceTransformer):
        s1 = VectorStore(model_name="fake", index_dir=idx)
        s1.build_from_documents(docs)
        s1.save()
        s2 = VectorStore.load(model_name="fake", index_dir=idx)
    assert len(s2._docs) == 2
    assert s2._docs[0].doc_id == "a"
    hits = s2.search("alpha", top_k=2)
    assert hits


def test_search_candidates_respects_cap_and_empty_store(tmp_path: Path) -> None:
    with patch("app.indexing.vector_store.SentenceTransformer", _FakeSentenceTransformer):
        s = VectorStore(model_name="fake", index_dir=tmp_path / "e")
    assert s.search_candidates("anything", 10) == []
    s.build_from_documents(
        [Document(doc_id=str(i), text=f"doc {i}", metadata={}) for i in range(3)]
    )
    out = s.search_candidates("doc", retrieve_k=2)
    assert len(out) == 2


def test_load_rejects_row_count_mismatch(tmp_path: Path) -> None:
    idx = tmp_path / "bad"
    with patch("app.indexing.vector_store.SentenceTransformer", _FakeSentenceTransformer):
        s = VectorStore(model_name="fake", index_dir=idx)
        s.build_from_documents([Document(doc_id="only", text="solo", metadata={})])
        s.save()
        extra = (
            '{"doc_id":"ghost","text":"mismatch","metadata":{}}\n'
        )
        with (idx / "docs.jsonl").open("a", encoding="utf-8") as f:
            f.write(extra)
        with pytest.raises(ValueError, match="does not match"):
            VectorStore.load(model_name="fake", index_dir=idx)
