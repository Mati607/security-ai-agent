from __future__ import annotations

from fastapi.testclient import TestClient


def test_mitre_catalog(api_client: TestClient) -> None:
    r = api_client.get("/mitre/catalog")
    assert r.status_code == 200
    data = r.json()
    assert data["technique_count"] > 50
    assert any(t["id"] == "TA0002" for t in data["tactics"])


def test_mitre_map_endpoint(api_client: TestClient) -> None:
    r = api_client.post(
        "/mitre/map",
        json={"text": "spear phishing attachment with macro enabled document"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "hits" in body
    tech_ids = {h["technique_id"] for h in body["hits"]}
    assert "T1566" in tech_ids or "T1204" in tech_ids


def test_mitre_map_with_context(api_client: TestClient) -> None:
    r = api_client.post(
        "/mitre/map-with-context",
        json={"alert": "powershell encoded command outbound beacon"},
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["num_context_docs"] >= 1
    assert "mitre" in data
    hits = data["mitre"]["hits"]
    assert isinstance(hits, list)


def test_case_mitre_map_persists_timeline(api_client: TestClient) -> None:
    c = api_client.post("/cases", json={"title": "MITRE case"})
    cid = c.json()["id"]
    r = api_client.post(
        f"/cases/{cid}/mitre/map",
        json={"text": "kerberoast against service accounts then golden ticket"},
    )
    assert r.status_code == 200
    payload = r.json()
    assert "mitre" in payload and "case" in payload
    kinds = {e["kind"] for e in payload["case"]["timeline"]}
    assert "mitre_mapping" in kinds
    tech_ids = {h["technique_id"] for h in payload["mitre"]["hits"]}
    assert "T1558" in tech_ids or "T1003" in tech_ids
