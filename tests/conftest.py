from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import patch

import numpy as np
import pytest

from app.indexing.vector_store import Document, VectorStore


class _FakeSentenceTransformer:
    """Tiny deterministic encoder so FAISS paths run without downloading weights."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def get_sentence_embedding_dimension(self) -> int:
        return 8

    def encode(self, texts: List[str], **kwargs) -> np.ndarray:
        del kwargs
        out = np.zeros((len(texts), 8), dtype=np.float32)
        for i, t in enumerate(texts):
            seed = abs(hash(t)) % (2**16)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(8).astype(np.float32)
            n = float(np.linalg.norm(vec)) or 1.0
            out[i, :] = vec / n
        return out


@pytest.fixture
def tmp_index_dir(tmp_path: Path) -> Path:
    d = tmp_path / "idx"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def vector_store_with_docs(tmp_index_dir: Path) -> VectorStore:
    docs = [
        Document(
            doc_id="host-a",
            text="suspicious powershell encoded command outbound",
            metadata={
                "group": "actorname",
                "key": r"C:\Windows\System32\powershell.exe",
                "num_events": 12,
                "first_timestamp": "2024-01-10T10:00:00Z",
                "last_timestamp": "2024-01-10T12:00:00Z",
            },
        ),
        Document(
            doc_id="host-b",
            text="routine windows update service traffic",
            metadata={
                "group": "actorname",
                "key": r"C:\Windows\System32\svchost.exe",
                "num_events": 3,
                "first_timestamp": "2024-01-09T09:00:00Z",
                "last_timestamp": "2024-01-09T09:05:00Z",
            },
        ),
        Document(
            doc_id="host-c",
            text="contacted external ip 203.0.113.50 over https",
            metadata={
                "group": "actorname",
                "key": r"C:\Tools\unknown.exe",
                "num_events": 50,
                "first_timestamp": "2024-01-11T08:00:00Z",
                "last_timestamp": "2024-01-11T18:30:00Z",
            },
        ),
    ]
    with patch("app.indexing.vector_store.SentenceTransformer", _FakeSentenceTransformer):
        store = VectorStore(model_name="fake-mini", index_dir=tmp_index_dir)
        store.build_from_documents(docs)
    return store

