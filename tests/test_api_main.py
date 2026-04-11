from __future__ import annotations

import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.cases.service import CaseInvestigationService
from app.cases.store import CaseStore
from app.config import Settings
from app.llm.retrieval import build_default_pipeline


def _fake_summarization_pipeline(*_args: Any, **_kwargs: Any):
    class _Summ:
        def __call__(self, prompt: str, **kw: Any) -> list[dict[str, str]]:
            del prompt, kw
            return [{"summary_text": "stub brief"}]

    return _Summ()


@pytest.fixture()
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


def test_healthz(api_client: TestClient) -> None:
    r = api_client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_search_returns_hits(api_client: TestClient) -> None:
    r = api_client.post("/search", json={"query": "powershell"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body


def test_search_advanced_alias_matches_search(api_client: TestClient) -> None:
    payload = {"query": "windows", "top_k": 2, "narrow_by_ioc_overlap": False}
    a = api_client.post("/search", json=payload).json()
    b = api_client.post("/search/advanced", json=payload).json()
    assert a == b


def test_search_with_metadata_filter(api_client: TestClient) -> None:
    r = api_client.post(
        "/search",
        json={
            "query": "traffic",
            "top_k": 5,
            "filters": {"max_num_events": 10},
        },
    )
    assert r.status_code == 200
    for row in r.json():
        assert row["metadata"]["num_events"] <= 10


def test_contextualize_stub(api_client: TestClient) -> None:
    r = api_client.post("/contextualize", json={"alert": "test alert text"})
    assert r.status_code == 200
    data = r.json()
    assert data["brief"] == "stub brief"
    assert data["num_context"] >= 1


def test_triage_returns_search_results(api_client: TestClient) -> None:
    r = api_client.post("/triage", json={"alert": "https traffic investigation"})
    assert r.status_code == 200
    data = r.json()
    assert "search_results" in data
    assert isinstance(data["search_results"], list)
