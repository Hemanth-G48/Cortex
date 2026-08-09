"""Idea 5 — arXiv metadata lookup + import flow tests (mocked HTTP)."""
from __future__ import annotations

import pytest

from app.services.kb import arxiv

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <summary>We propose a new simple network architecture.</summary>
  </entry>
</feed>
"""


class _FakeResponse:
    def __init__(self, status_code=200, text=ATOM):
        self.status_code = status_code
        self.text = text


class TestArxivIdExtraction:
    def test_extracts_from_plain_id_url_and_filename(self):
        assert arxiv.extract_arxiv_id("1706.03762") == "1706.03762"
        assert arxiv.extract_arxiv_id("arXiv:1706.03762v3") == "1706.03762"
        assert arxiv.extract_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
        assert arxiv.extract_arxiv_id("1706.03762.pdf") == "1706.03762"
        assert arxiv.extract_arxiv_id("no id here") is None


@pytest.fixture()
def fresh_cache(monkeypatch):
    """Isolate the module-level arXiv lookup cache per test."""
    monkeypatch.setattr(arxiv, "_CACHE", {})


class TestFetchMetadata:
    def test_parses_atom_response(self, monkeypatch, fresh_cache):
        calls = []

        def fake_get(url, params, timeout):
            calls.append((url, params))
            return _FakeResponse()

        monkeypatch.setattr(arxiv.httpx, "get", fake_get)
        meta = arxiv.fetch_arxiv_metadata("1706.03762")
        assert meta["arxiv_id"] == "1706.03762"
        assert meta["title"] == "Attention Is All You Need"
        assert "Ashish Vaswani" in meta["authors"]
        assert "network architecture" in meta["abstract"]
        assert ("http://export.arxiv.org/api/query", {"id_list": "1706.03762"}) in calls

    def test_caches_by_id(self, monkeypatch, fresh_cache):
        calls = []

        def fake_get(url, params, timeout):
            calls.append(1)
            return _FakeResponse()

        monkeypatch.setattr(arxiv.httpx, "get", fake_get)
        arxiv.fetch_arxiv_metadata("1706.03762")
        arxiv.fetch_arxiv_metadata("1706.03762")
        assert len(calls) == 1  # second call served from cache

    def test_fails_gracefully_offline(self, monkeypatch, fresh_cache):
        def fake_get(url, params, timeout):
            raise Exception("network unreachable")  # noqa: BLE001

        monkeypatch.setattr(arxiv.httpx, "get", fake_get)
        assert arxiv.fetch_arxiv_metadata("1706.03762") is None

    def test_non_200_returns_none(self, monkeypatch, fresh_cache):
        monkeypatch.setattr(
            arxiv.httpx, "get", lambda *a, **k: _FakeResponse(status_code=500)
        )
        assert arxiv.fetch_arxiv_metadata("1706.03762") is None


AUTH = "Authorization"


class TestImportFlow:
    def test_import_creates_document_with_metadata(self, client, monkeypatch, fresh_cache):
        token = _signup(client)
        monkeypatch.setattr(
            arxiv.httpx, "get", lambda *a, **k: _FakeResponse()
        )
        resp = client.post(
            "/api/kb/papers/import",
            json={"arxiv_id": "1706.03762"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["metadata_fetched"] is True
        assert data["document"]["title"] == "Attention Is All You Need"
        assert data["document"]["metadata"]["arxiv_id"] == "1706.03762"
        assert data["document"]["chunk_count"] >= 1

    def test_import_offline_still_creates_document(self, client, monkeypatch, fresh_cache):
        token = _signup(client)

        def fake_get(url, params, timeout):
            raise Exception("offline")  # noqa: BLE001

        monkeypatch.setattr(arxiv.httpx, "get", fake_get)
        resp = client.post(
            "/api/kb/papers/import",
            json={"arxiv_id": "1706.03762"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text  # never 500 offline
        data = resp.json()
        assert data["metadata_fetched"] is False
        assert data["document"]["title"] == "arXiv:1706.03762"

    def test_import_rejects_unrecognized_id(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/kb/papers/import",
            json={"arxiv_id": "not-an-arxiv-id"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400


def _signup(client, uname="arxiv-user", email="arxiv@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Arxiv", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]
