"""Idea 32 — grounded explanation tests.

Mocked retrieval + generation, citation presence/absence handling, depth
variants, fallback, budget.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import KbGenerationLog
from app.services.security import decode_bearer_token


def _signup(client, uname="exp-user", email="exp@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Exp", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


class _FakeSearcher:
    """Stand-in for KbSearcher returning crafted unified results."""

    def __init__(self, items):
        self._items = items

    def search(self, query, mode=None, limit=20, page=1):
        return {"items": self._items[:limit]}


def _chunk(item_id, doc_id, title, snippet, heading="Physics"):
    return {
        "chunk_id": item_id, "document_id": doc_id, "seq": 0, "title": title,
        "snippet": snippet, "score": 0.9, "mode": "hybrid",
        "source_path": f"{title.lower()}.md", "heading_path": heading,
        "doc_type": "md", "doc_date": None, "char_start": 0, "char_end": 200,
        "sources": ["fts"],
    }


ITEMS = [
    _chunk(11, 1, "Relativity", "Einstein developed the theory of relativity."),
    _chunk(12, 2, "Photons", "Light travels as photons."),
]


class TestExplainEndpoint:
    def test_mocked_cited_answer(self, client):
        token = _signup(client)
        with patch(
            "app.services.kb.explain.KbSearcher",
            lambda db, uid: _FakeSearcher(ITEMS),
        ), patch(
            "app.services.ai_client.generate_json",
            return_value={"explanation": "Relativity is a theory [1].", "citations": [1]},
        ):
            r = client.post(
                "/api/kb/explain",
                json={"concept": "relativity", "depth": "overview"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["depth"] == "overview"
        assert "[1]" in data["explanation"]
        assert data["citations"] and data["citations"][0]["chunk_id"] == 11
        assert data["citations"][0]["document_id"] == 1

    def test_depth_variants(self, client):
        token = _signup(client)
        for depth in ("overview", "deep_dive", "eli5", "analogy", "derivation"):
            with patch(
                "app.services.kb.explain.KbSearcher",
                lambda db, uid: _FakeSearcher(ITEMS),
            ), patch(
                "app.services.ai_client.generate_json",
                return_value={"explanation": f"{depth} text", "citations": [1]},
            ):
                r = client.post(
                    "/api/kb/explain",
                    json={"concept": "x", "depth": depth},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert r.status_code == 200, r.text
            assert r.json()["depth"] == depth

    def test_invalid_depth_rejected(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/explain",
            json={"concept": "x", "depth": "bogus"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_missing_citations_regenerates_once(self, client):
        token = _signup(client)
        calls = {"n": 0}

        def side_effect(prompt, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"explanation": "No citations here.", "citations": []}
            return {"explanation": "Now cited [1].", "citations": [1]}

        with patch(
            "app.services.kb.explain.KbSearcher",
            lambda db, uid: _FakeSearcher(ITEMS),
        ), patch("app.services.ai_client.generate_json", side_effect=side_effect):
            r = client.post(
                "/api/kb/explain",
                json={"concept": "relativity"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200
        assert r.json()["citations"], r.json()
        assert calls["n"] == 2

    def test_fallback_when_ai_disabled(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        with patch(
            "app.services.kb.explain.KbSearcher",
            lambda db, uid: _FakeSearcher([]),
        ):
            r = client.post(
                "/api/kb/explain",
                json={"concept": "quantum", "depth": "eli5"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fallback"] is True
        assert data["explanation"]

    def test_budget_cap(self, client, db_session):
        from app.config import settings
        original = settings.AI_ENABLED
        settings.AI_ENABLED = True
        try:
            token = _signup(client, "exp-budget", "expb@test.com")
            user_id = decode_bearer_token(token)["user_id"]
            for _ in range(settings.KB_DAILY_GEN_LIMIT):
                db_session.add(KbGenerationLog(user_id=user_id, kind="explain"))
            db_session.commit()
            r = client.post(
                "/api/kb/explain",
                json={"concept": "x", "depth": "overview"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 429
        finally:
            settings.AI_ENABLED = original
