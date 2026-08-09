"""Idea 21 — full-text search (FTS5) tests.

Covers the FTS5 virtual table + trigger sync, query builder (prefix/phrase/
escaping), per-user isolation, snippet markers, and the keyword search
endpoint. The test client inherits the app's ``get_db`` override from
conftest, so the FTS index is created against the in-memory SQLite engine.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.kb import fts


def _signup(client, uname="fts-user", email="fts@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "FTS", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _scan_md(client, token, root, texts):
    """Write ``n`` markdown files into ``root`` and scan it as a source."""
    for i, text in enumerate(texts):
        (root / f"doc{i}.md").write_text(text)
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "source_type": "vault_folder", "root_path": str(root)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    src = resp.json()
    scan = client.post(
        f"/api/kb/sources/{src['id']}/scan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert scan.status_code == 200, scan.text
    return src


class TestQueryBuilder:
    def test_prefix_matching(self):
        # Bare terms become prefix matches for typo tolerance (Idea 24).
        q = fts.build_fts_query("machine")
        assert q == "machine*"

    def test_phrase_preserved(self):
        q = fts.build_fts_query('machine "deep learning"')
        assert '"deep learning"' in q
        assert "machine*" in q

    def test_short_tokens_dropped(self):
        # "a" is below KB_FTS_MIN_TOKEN.
        q = fts.build_fts_query("a b cat")
        assert "cat*" in q
        assert "a*" not in q

    def test_special_chars_escaped_in_phrase(self):
        # Special chars survive inside a quoted phrase → they must be escaped.
        q = fts.build_fts_query('"c++ and rust"')
        assert "\\+" in q
        assert "rust" in q

    def test_empty_returns_empty(self):
        assert fts.build_fts_query("   ") == ""


class TestFtsIndexAndSearch:
    def test_index_and_keyword_search(self, client, tmp_path):
        token = _signup(client)
        _scan_md(client, token, tmp_path, [
            "# Alpha\n\nThe quick brown fox jumps over the lazy dog.",
            "# Beta\n\nMachine learning improves retrieval systems.",
        ])

        resp = client.get(
            "/api/kb/search", params={"q": "machine", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["mode"] == "keyword"
        assert data["total"] >= 1
        assert any("machine" in i["title"].lower() or i["doc_type"] == "md"
                   for i in data["items"])

    def test_per_user_isolation(self, client, tmp_path):
        t1 = _signup(client, "u1", "u1@test.com")
        t2 = _signup(client, "u2", "u2@test.com")
        _scan_md(client, t1, tmp_path, ["unique-word-alpha content"])
        (tmp_path / "other.md").write_text("unique-word-alpha content")
        resp = client.post(
            "/api/kb/sources",
            json={"name": "V2", "root_path": str(tmp_path)},
            headers={"Authorization": f"Bearer {t2}"},
        )
        src2 = resp.json()
        client.post(f"/api/kb/sources/{src2['id']}/scan",
                    headers={"Authorization": f"Bearer {t2}"})

        r1 = client.get("/api/kb/search", params={"q": "unique-word", "mode": "keyword"},
                        headers={"Authorization": f"Bearer {t1}"})
        r2 = client.get("/api/kb/search", params={"q": "unique-word", "mode": "keyword"},
                        headers={"Authorization": f"Bearer {t2}"})
        assert r1.json()["total"] >= 1
        assert r2.json()["total"] >= 1
        # Cross-user: user3 sees nothing.
        t3 = _signup(client, "u3", "u3@test.com")
        r3 = client.get("/api/kb/search", params={"q": "unique-word", "mode": "keyword"},
                        headers={"Authorization": f"Bearer {t3}"})
        assert r3.json()["total"] == 0

    def test_snippet_markers_present(self, client, tmp_path):
        token = _signup(client)
        _scan_md(client, token, tmp_path, [
            "A document about gradient descent optimization algorithms.",
        ])
        resp = client.get(
            "/api/kb/search", params={"q": "gradient", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        # <mark> markers wrap the matched term in the snippet.
        assert any("<mark>" in i["snippet"] for i in data["items"])

    def test_bad_query_400(self, client, tmp_path):
        token = _signup(client)
        resp = client.get("/api/kb/search", params={"q": ""},
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (400, 422)
