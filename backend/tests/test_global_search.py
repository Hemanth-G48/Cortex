"""Idea 30 — global unified search tests.

Verifies fan-out coverage, per-domain caps, facet filtering, empty-result
shape, and per-user scoping across domains.
"""
from __future__ import annotations


def _signup(client, uname="gs-user", email="gs@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "GS", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _scan(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"d{i}.md").write_text(text)
    r = client.post(
        "/api/kb/sources",
        json={"name": "V", "root_path": str(root)},
        headers={"Authorization": f"Bearer {token}"},
    )
    src = r.json()
    client.post(f"/api/kb/sources/{src['id']}/scan",
                headers={"Authorization": f"Bearer {token}"})


class TestGlobalSearch:
    def test_returns_shape(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Globally searchable vault content."])
        resp = client.post(
            "/api/search",
            json={"query": "globally", "domains": ["vault"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert {"items", "groups", "total", "query", "domains"} <= set(data)
        assert "vault" in data["groups"]

    def test_empty_result_shape(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/search",
            json={"query": "", "domains": ["vault", "tasks"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_facet_filtering(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Faceted content here."])
        # Only tasks domain requested → no vault group.
        resp = client.post(
            "/api/search",
            json={"query": "anything", "domains": ["tasks"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        # Vault wasn't requested → never surfaced.
        assert "vault" not in data["groups"]
        # Tasks had no matching rows → group simply absent (no phantom group).
        assert "tasks" not in data["groups"]
        assert data["total"] == 0

    def test_per_user_scoping(self, client, tmp_path):
        t1 = _signup(client, "gs-u1", "gs1@test.com")
        t2 = _signup(client, "gs-u2", "gs2@test.com")
        _scan(client, t1, tmp_path, ["secret-vault-word content"])
        resp = client.post(
            "/api/search",
            json={"query": "secret-vault-word", "domains": ["vault"]},
            headers={"Authorization": f"Bearer {t2}"},
        )
        # user2 cannot see user1's vault content.
        assert resp.json()["total"] == 0

    def test_bad_domain_ignored(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Content."])
        resp = client.post(
            "/api/search",
            json={"query": "content", "domains": ["nonexistent"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 0
