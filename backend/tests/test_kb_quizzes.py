"""Idea 33 — note-quiz tests.

Note → quiz happy path (mocked), min-content 422, provenance link recorded,
deterministic fallback quiz.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import KbQuizLink, Quiz


def _signup(client, uname="qz-user", email="qz@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Qz", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload(client, token, name="note.md", content=b"# Title\n\n" + b"word " * 200):
    resp = client.post(
        "/api/kb/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, "test.md")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]["id"]


class TestNoteQuiz:
    def test_mocked_note_quiz(self, client, db_session):
        token = _signup(client)
        doc_id = _upload(client, token)
        mock = {
            "questions": [
                {"question": "Q1?", "options": ["a", "b", "c", "d"], "correct_index": 0, "explanation": "e1"},
                {"question": "Q2?", "options": ["a", "b", "c", "d"], "correct_index": 1, "explanation": "e2"},
            ]
        }
        with patch("app.services.ai_client.generate_json", return_value=mock):
            r = client.post(
                "/api/kb/quizzes",
                json={"document_id": doc_id, "num_questions": 2, "difficulty": "easy"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["document_id"] == doc_id
        assert len(data["questions"]) == 2
        assert data["difficulty"] == "easy"

        # Provenance link recorded (phrase 26).
        link = db_session.query(KbQuizLink).filter_by(quiz_id=data["id"]).first()
        assert link is not None and link.document_id == doc_id
        quiz = db_session.query(Quiz).get(data["id"])
        assert quiz.unit_id is None  # note quizzes have no curriculum unit

    def test_reverse_provenance_endpoint(self, client, db_session):
        token = _signup(client)
        doc_id = _upload(client, token)
        with patch("app.services.ai_client.generate_json", return_value={
            "questions": [{"question": "Q?", "options": ["a", "b", "c", "d"],
                           "correct_index": 0, "explanation": "e"}]}):
            r = client.post(
                "/api/kb/quizzes",
                json={"document_id": doc_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        quiz_id = r.json()["id"]
        r2 = client.get(
            f"/api/kb/quizzes/{quiz_id}/document",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["id"] == doc_id

    def test_min_content_gateway_422(self, client):
        token = _signup(client)
        doc_id = _upload(client, token, content=b"tiny")
        r = client.post(
            "/api/kb/quizzes",
            json={"document_id": doc_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_fallback_quiz_when_ai_disabled(self, client, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        doc_id = _upload(client, token)
        r = client.post(
            "/api/kb/quizzes",
            json={"document_id": doc_id, "num_questions": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        # Deterministic demo quiz always has 3 questions.
        assert len(r.json()["questions"]) == 3

    def test_per_user_isolation(self, client):
        token_a = _signup(client, "qz-a", "qza@test.com")
        token_b = _signup(client, "qz-b", "qzb@test.com")
        doc_id = _upload(client, token_a)
        r = client.post(
            "/api/kb/quizzes",
            json={"document_id": doc_id},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r.status_code == 404
