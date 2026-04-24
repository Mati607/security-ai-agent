from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_register_login_me(api_client: TestClient) -> None:
    uname = f"u_{uuid.uuid4().hex[:12]}"
    pw = "LongEnough1!"
    reg = api_client.post("/auth/register", json={"username": uname, "password": pw})
    assert reg.status_code == 201
    assert reg.json()["username"] == uname.lower()

    tok = api_client.post(
        "/auth/token",
        data={"username": uname, "password": pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert tok.status_code == 200
    body = tok.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] >= 60

    me = api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == uname.lower()


def test_register_duplicate_username(api_client: TestClient) -> None:
    uname = f"d_{uuid.uuid4().hex[:12]}"
    pw = "LongEnough1!"
    assert api_client.post("/auth/register", json={"username": uname, "password": pw}).status_code == 201
    dup = api_client.post("/auth/register", json={"username": uname.upper(), "password": pw + "x"})
    assert dup.status_code == 409


def test_login_invalid_password(api_client: TestClient) -> None:
    uname = f"l_{uuid.uuid4().hex[:12]}"
    pw = "LongEnough1!"
    assert api_client.post("/auth/register", json={"username": uname, "password": pw}).status_code == 201
    bad = api_client.post(
        "/auth/token",
        data={"username": uname, "password": "wrong-pass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert bad.status_code == 401


def test_case_isolation_between_users(api_client: TestClient) -> None:
    def _register_and_token(name: str, pw: str) -> dict[str, str]:
        assert api_client.post("/auth/register", json={"username": name, "password": pw}).status_code == 201
        t = api_client.post(
            "/auth/token",
            data={"username": name, "password": pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()["access_token"]
        return {"Authorization": f"Bearer {t}"}

    pw = "LongEnough1!"
    h_alice = _register_and_token(f"alice_{uuid.uuid4().hex[:8]}", pw)
    h_bob = _register_and_token(f"bob_{uuid.uuid4().hex[:8]}", pw)

    cid = api_client.post("/cases", json={"title": "Alice secret"}, headers=h_alice).json()["id"]
    assert api_client.get(f"/cases/{cid}", headers=h_alice).status_code == 200
    assert api_client.get(f"/cases/{cid}", headers=h_bob).status_code == 404
