"""Idea 31 — document summary tests.

Cache hit, regenerate on hash change, budget cap, fallback shape, and
per-user isolation.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import KbGenerationLog, KbSummary
from app.services.kb import summarize
from app.services.security import decode_bearer_token


def _signup(client, uname="sum-user", email="sum@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Sum", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload(client, token, name="note.md", content=b"# Title\n\nLots of content."):
    resp = client.post(
        "/api/kb/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, "test.md")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]["id"]


class TestSummaryEndpoint:
    def test_fallback_shape(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        doc_id = _upload(client, token)
        r = client.get(
            f"/api/kb/documents/{doc_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cached"] is False
        s = data["summary"]
        assert set(s) >= {"content", "key_points", "definitions", "open_questions"}
        assert isinstance(s["content"], str) and s["content"]
        assert isinstance(s["key_points"], list)

    def test_cache_hit(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        doc_id = _upload(client, token)
        first = client.get(
            f"/api/kb/documents/{doc_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert first["cached"] is False
        second = client.get(
            f"/api/kb/documents/{doc_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert second["cached"] is True

    def test_mocked_ai_structured_summary(self, client):
        token = _signup(client)
        doc_id = _upload(client, token)
        mock = {
            "summary": "A TL;DR.",
            "key_points": ["One", "Two"],
            "definitions": [{"term": "X", "definition": "X is Y"}],
            "open_questions": ["What next?"],
        }
        with patch("app.services.ai_client.generate_json", return_value=mock):
            r = client.post(
                f"/api/kb/documents/{doc_id}/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        s = r.json()["summary"]
        assert s["content"] == "A TL;DR."
        assert s["definitions"][0]["term"] == "X"
        assert s["open_questions"] == ["What next?"]

    def test_budget_cap(self, client, db_session):
        from app.config import settings
        original = settings.AI_ENABLED
        settings.AI_ENABLED = True
        try:
            token = _signup(client, "sum-budget", "sumb@test.com")
            user_id = decode_bearer_token(token)["user_id"]
            doc_id = _upload(client, token)
            # Exhaust the shared Phase 4 budget for this user.
            for _ in range(settings.KB_DAILY_GEN_LIMIT):
                db_session.add(KbGenerationLog(user_id=user_id, kind="summary"))
            db_session.commit()
            r = client.post(
                f"/api/kb/documents/{doc_id}/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 429
        finally:
            settings.AI_ENABLED = original

    def test_per_user_isolation(self, client):
        token_a = _signup(client, "sum-a", "suma@test.com")
        token_b = _signup(client, "sum-b", "sumb2@test.com")
        doc_id = _upload(client, token_a)
        r = client.get(
            f"/api/kb/documents/{doc_id}/summary",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r.status_code == 404


class TestSummaryService:
    def test_regenerate_on_hash_change(self, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        from app.models import KbDocument

        doc = KbDocument(user_id=1, title="T", doc_type="md",
                         extracted_text="AAA content here.", char_count=20)
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        r1 = summarize.get_or_generate_summary(db_session, 1, doc)
        assert r1["cached"] is False
        r2 = summarize.get_or_generate_summary(db_session, 1, doc)
        assert r2["cached"] is True

        # Change content → hash mismatch → regenerate.
        doc.extracted_text = "BBB different content now."
        db_session.commit()
        r3 = summarize.get_or_generate_summary(db_session, 1, doc)
        assert r3["cached"] is False

    def test_ai_failure_falls_back(self, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", True)
        from app.models import KbDocument

        doc = KbDocument(user_id=1, title="T", doc_type="md",
                         extracted_text="# H1\n\nA longer sentence here.", char_count=30)
        db_session.add(doc)
        db_session.commit()
        with patch("app.services.ai_client.generate_json", return_value=None):
            result = summarize.get_or_generate_summary(db_session, 1, doc)
        assert result["summary"]["content"]
        assert result["cached"] is False
