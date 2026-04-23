from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(api_client: TestClient) -> None:
    r = api_client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_info(api_client: TestClient) -> None:
    r = api_client.get("/index/info")
    assert r.status_code == 200
    data = r.json()
    assert data["embedding_model_name"] == "fake-mini"
    assert data["embedding_dimension"] == 8
    assert data["document_count"] == 3
    assert data["faiss_vector_total"] == 3
    assert data["persisted_index_files"] is False
    assert data["index_consistent"] is True


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
