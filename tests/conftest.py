from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, List
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.cases.service import CaseInvestigationService
from app.cases.store import CaseStore
from app.config import Settings
from app.indexing.vector_store import Document, VectorStore
from app.llm.retrieval import build_default_pipeline


def _fake_summarization_pipeline(*_args: Any, **_kwargs: Any):
    class _Summ:
        def __call__(self, prompt: str, **kw: Any) -> list[dict[str, str]]:
            del prompt, kw
            return [{"summary_text": "stub brief"}]

    return _Summ()


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


@pytest.fixture
def api_client(vector_store_with_docs, tmp_index_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.llm.contextualize.pipeline",
        _fake_summarization_pipeline,
    )

    def _mock_load(cls, model_name: str, index_dir):  # noqa: ANN001
        del cls, model_name, index_dir
        return vector_store_with_docs

    monkeypatch.setattr(
        "app.indexing.vector_store.VectorStore.load",
        classmethod(_mock_load),
    )

    sys.modules.pop("app.api.main", None)
    import app.api.main as main

    settings = Settings(
        embedding_model_name="fake-mini",
        index_dir=tmp_index_dir,
        search_top_k=5,
        retrieve_multiplier=2,
        retrieve_max_candidates=50,
        summarizer_model_name="google/flan-t5-small",
        rerank_enabled=False,
    )
    monkeypatch.setattr(main, "settings", settings)
    monkeypatch.setattr(main, "_store", vector_store_with_docs)
    pipeline = build_default_pipeline(vector_store_with_docs, settings)
    monkeypatch.setattr(main, "_pipeline", pipeline)
    case_store = CaseStore(tmp_path / "cases_api.db")
    case_store.init_db()
    monkeypatch.setattr(main, "_case_store", case_store)
    monkeypatch.setattr(
        main,
        "_case_service",
        CaseInvestigationService(
            case_store,
            pipeline,
            main._contextualizer,
            settings,
        ),
    )
    return TestClient(main.app)


@pytest.fixture
def auth_headers(api_client: TestClient) -> dict[str, str]:
    """Bearer token for a freshly registered analyst (per test client / DB)."""

    uname = f"analyst_{uuid.uuid4().hex[:10]}"
    pw = "SecurePass1!"
    r = api_client.post("/auth/register", json={"username": uname, "password": pw})
    assert r.status_code == 201, r.text
    r2 = api_client.post(
        "/auth/token",
        data={"username": uname, "password": pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r2.status_code == 200, r2.text
    token = r2.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

