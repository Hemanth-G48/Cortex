"""Tests for the brain dump API endpoints."""

from app.services.security import create_bearer_token


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    return resp.json()["token"]


def test_get_returns_null_content_when_no_row(client):
    token = _get_token(client)
    resp = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] is None


def test_put_creates_row_then_get_returns_content(client):
    token = _get_token(client)

    resp = client.put("/api/braindumps", json={"content": "My first brain dump"}, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "My first brain dump"
    assert data["id"] is not None

    resp2 = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp2.json()["content"] == "My first brain dump"


def test_put_again_updates_content_same_row(client):
    token = _get_token(client)

    client.put("/api/braindumps", json={"content": "First version"}, headers={
        "Authorization": f"Bearer {token}",
    })
    first = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token}"}).json()
    first_id = first["id"]

    client.put("/api/braindumps", json={"content": "Updated version"}, headers={
        "Authorization": f"Bearer {token}",
    })
    second = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token}"}).json()

    assert second["content"] == "Updated version"
    assert second["id"] == first_id


def test_second_user_has_separate_row(client):
    token1 = _get_token(client)

    signup = client.post("/api/auth/signup", json={
        "name": "Second User",
        "username": "seconduser",
        "email": "second@test.com",
        "password": "secret123",
        "role": "student",
    })
    assert signup.status_code == 201
    token2 = signup.json()["token"]

    client.put("/api/braindumps", json={"content": "User 1 content"}, headers={
        "Authorization": f"Bearer {token1}",
    })
    client.put("/api/braindumps", json={"content": "User 2 content"}, headers={
        "Authorization": f"Bearer {token2}",
    })

    resp1 = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token1}"}).json()
    resp2 = client.get("/api/braindumps", headers={"Authorization": f"Bearer {token2}"}).json()

    assert resp1["content"] == "User 1 content"
    assert resp2["content"] == "User 2 content"
    assert resp1["id"] != resp2["id"]


def test_second_put_same_user_no_integrity_error(client):
    token = _get_token(client)

    resp = client.put("/api/braindumps", json={"content": "Initial content"}, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200

    resp2 = client.put("/api/braindumps", json={"content": "Updated content"}, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp2.status_code == 200
    assert resp2.json()["content"] == "Updated content"
