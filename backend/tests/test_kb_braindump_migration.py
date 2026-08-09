"""Idea 40 — brain-dump → draft note tests.

Save creates a draft, repeated saves are idempotent, quick-file transitions
status, AI splitting (mocked + fallback), and empty saves create nothing.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import KbDocument, KbDocumentTag, KbTag
from app.services.security import decode_bearer_token


def _signup(client, uname="bd-user", email="bd@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Bd", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _put(client, token, content):
    return client.put(
        "/api/braindumps/",
        json={"content": content},
        headers={"Authorization": f"Bearer {token}"},
    )


LONG_TEXT = ("# Brain\n\n" + ("This is a long paragraph about study techniques and "
                              "memory retention. " * 30) + "\n\n" +
             ("Another distinct paragraph on focus and flow states. " * 20))


class TestDraftCreation:
    def test_save_creates_draft(self, client, db_session):
        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        r = _put(client, token, "First draft of my study notes.")
        assert r.status_code == 200, r.text
        linked_id = r.json()["linked_document_id"]
        assert linked_id is not None
        doc = db_session.query(KbDocument).get(linked_id)
        assert doc.status == "draft"
        assert doc.user_id == user_id
        assert doc.chunks  # draft is chunked

    def test_repeated_saves_idempotent(self, client, db_session):
        token = _signup(client)
        first = _put(client, token, "Same content.").json()["linked_document_id"]
        second = _put(client, token, "Same content.").json()["linked_document_id"]
        assert first == second
        third = _put(client, token, "Updated content now.").json()["linked_document_id"]
        assert third == first  # still the same draft row
        assert db_session.query(KbDocument).filter_by(status="draft").count() == 1

    def test_empty_save_no_draft(self, client, db_session):
        token = _signup(client)
        r = _put(client, token, "")
        assert r.status_code == 200
        assert r.json()["linked_document_id"] is None
        assert db_session.query(KbDocument).filter_by(status="draft").count() == 0

    def test_get_returns_linked_document(self, client):
        token = _signup(client)
        _put(client, token, "Captured today.")
        r = client.get(
            "/api/braindumps/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["linked_document_id"] is not None

    def test_widget_backward_compatible(self, client):
        """The PUT response still carries the legacy content field."""
        token = _signup(client)
        r = _put(client, token, "Legacy content.")
        data = r.json()
        assert data["content"] == "Legacy content."
        assert "id" in data and "user_id" in data


class TestQuickFile:
    def test_file_transitions_draft_to_new(self, client, db_session):
        token = _signup(client)
        linked = _put(client, token, "Draft to file.").json()["linked_document_id"]
        r = client.post(
            f"/api/kb/documents/{linked}/file",
            json={"title": "Filed Note", "tags": ["physics", "notes"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        doc = db_session.query(KbDocument).get(linked)
        assert doc.status == "new"
        assert doc.title == "Filed Note"
        tag_names = {
            t.name
            for t in db_session.query(KbTag)
            .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
            .filter(KbDocumentTag.document_id == linked)
            .all()
        }
        assert {"physics", "notes"} <= tag_names

    def test_file_rejects_non_draft(self, client):
        token = _signup(client)
        linked = _put(client, token, "Draft.").json()["linked_document_id"]
        client.post(
            f"/api/kb/documents/{linked}/file",
            json={"title": "Filed"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Second file attempt → already 'new', not a draft anymore.
        r = client.post(
            f"/api/kb/documents/{linked}/file",
            json={"title": "Again"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400


class TestSplitting:
    def test_split_long_dump_fallback(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        linked = _put(client, token, LONG_TEXT).json()["linked_document_id"]
        r = client.post(
            f"/api/kb/documents/{linked}/split",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fallback"] is True
        assert data["sections_applied"] >= 1
        # Headings were applied to the draft text.
        fresh = db_session.query(KbDocument).get(linked)
        assert fresh.extracted_text.count("\n# ") >= 1

    def test_split_mocked_sections(self, client):
        token = _signup(client)
        linked = _put(client, token, LONG_TEXT).json()["linked_document_id"]
        mock = {"sections": [
            {"title": "Techniques", "char_start": 0},
            {"title": "Focus", "char_start": 500},
        ]}
        with patch("app.services.ai_client.generate_json", return_value=mock):
            r = client.post(
                f"/api/kb/documents/{linked}/split",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        assert r.json()["sections_applied"] == 1
        assert r.json()["sections"][0]["title"] == "Techniques"

    def test_split_short_dump_rejected(self, client):
        token = _signup(client)
        linked = _put(client, token, "Too short.").json()["linked_document_id"]
        r = client.post(
            f"/api/kb/documents/{linked}/split",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422
