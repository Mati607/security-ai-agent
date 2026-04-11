from __future__ import annotations

from fastapi.testclient import TestClient


def test_cases_crud_flow(api_client: TestClient) -> None:
    r = api_client.post(
        "/cases",
        json={
            "title": "Suspicious WMI 203.0.113.88",
            "tags": ["wmi"],
            "summary": "Parent: powershell.exe",
        },
    )
    assert r.status_code == 200
    created = r.json()
    cid = created["id"]
    assert created["title"].startswith("Suspicious")

    g = api_client.get(f"/cases/{cid}")
    assert g.status_code == 200
    assert g.json()["id"] == cid

    p = api_client.patch(f"/cases/{cid}", json={"status": "in_progress"})
    assert p.status_code == 200
    assert p.json()["status"] == "in_progress"

    lst = api_client.get("/cases?limit=10")
    assert lst.status_code == 200
    assert any(row["id"] == cid for row in lst.json())


def test_cases_note_and_iocs(api_client: TestClient) -> None:
    r = api_client.post("/cases", json={"title": "IOC rollup test"})
    cid = r.json()["id"]
    n = api_client.post(
        f"/cases/{cid}/notes",
        json={"body": "C2 observed at 198.51.100.10 and evil.example.com"},
    )
    assert n.status_code == 200
    iocs = api_client.get(f"/cases/{cid}/iocs")
    assert iocs.status_code == 200
    data = iocs.json()
    assert "198.51.100.10" in data["ipv4"]
    assert any("evil.example.com" in d for d in data["domains"])


def test_cases_export_html(api_client: TestClient) -> None:
    r = api_client.post("/cases", json={"title": "HTML export"})
    cid = r.json()["id"]
    h = api_client.get(f"/cases/{cid}/export.html")
    assert h.status_code == 200
    assert "text/html" in h.headers.get("content-type", "")
    assert "HTML export" in h.text
    assert "IOC rollup" in h.text


def test_cases_search_run_attaches_snapshot(api_client: TestClient) -> None:
    r = api_client.post("/cases", json={"title": "Search attach"})
    cid = r.json()["id"]
    sr = api_client.post(
        f"/cases/{cid}/snapshots/search-run",
        json={"query": "powershell suspicious", "top_k": 3},
    )
    assert sr.status_code == 200
    detail = sr.json()
    kinds = {e["kind"] for e in detail["timeline"]}
    assert "search_snapshot" in kinds


def test_cases_triage_snapshot(api_client: TestClient) -> None:
    r = api_client.post("/cases", json={"title": "Triage attach"})
    cid = r.json()["id"]
    tr = api_client.post(
        f"/cases/{cid}/snapshots/triage",
        json={"alert": "encoded powershell beacon"},
        headers={"content-type": "application/json"},
    )
    assert tr.status_code == 200
    body = tr.json()
    assert body["triage"]["brief"] == "stub brief"
    assert body["case"]["timeline"]


def test_cases_404(api_client: TestClient) -> None:
    assert api_client.get("/cases/not-a-real-id").status_code == 404
