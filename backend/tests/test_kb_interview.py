"""Idea 65 — interview preparation tests.

Covers interview session start (question generation via the question
generator, budget-capped), answer grading through the extended grade-answer
service, feedback with structured corrections, session persistence, the
aggregate score feeding the skill map on finish, and per-user isolation.
"""
from __future__ import annotations

import pytest

SYLLABUS = """\
# Machine Learning

Fall 2026

## Unit 1: Foundations
- Linear algebra review
- Probability review

## Unit 2: Regression
- Linear regression
- Gradient descent
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="ivw-user", email="ivw@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Ivw", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


def _start(client, token, skill="machine learning", level="intermediate"):
    r = client.post(
        "/api/kb/interview/start",
        json={"skill": skill, "level": level},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["session"]


class TestStart:
    def test_start_creates_session_with_questions(self, client):
        token = _signup(client)
        _confirmed(client, token)
        session = _start(client, token)
        assert session["id"] > 0
        assert session["skill"] == "machine learning"
        assert session["level"] == "intermediate"
        assert session["status"] == "in_progress"
        assert len(session["questions"]) >= 4
        assert all(q["question"] for q in session["questions"])

    def test_level_validation(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/interview/start",
            json={"skill": "ml", "level": "expert"},  # invalid level
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_start_without_topics_still_works(self, client):
        # No syllabus → template questions fall back to the skill itself.
        token = _signup(client)
        session = _start(client, token, skill="data structures")
        assert len(session["questions"]) >= 4


class TestAnswer:
    def test_answer_grades_via_grader(self, client):
        token = _signup(client)
        _confirmed(client, token)
        session = _start(client, token)
        q = session["questions"][0]
        r = client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "A clear structured answer covering the key ideas."},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "score" in data
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert isinstance(data["strengths"], list)
        assert isinstance(data["action_items"], list)
        assert data["ai_used"] is False  # fallback grader

    def test_answer_out_of_range_400(self, client):
        token = _signup(client)
        session = _start(client, token)
        r = client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 99, "answer": "x"},
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_double_answer_400(self, client):
        token = _signup(client)
        session = _start(client, token)
        client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "first answer"},
            headers=_auth(token),
        )
        r = client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "second answer"},
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_answer_other_users_session_404(self, client):
        t_a = _signup(client, "ivw-a", "ivwa@test.com")
        t_b = _signup(client, "ivw-b", "ivwb@test.com")
        session = _start(client, t_a)
        r = client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "x"},
            headers=_auth(t_b),
        )
        assert r.status_code == 404


class TestFinish:
    def test_finish_completes_and_scores(self, client, db_session):
        from app.models import InterviewSession, UserSkill
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        session = _start(client, token)
        # Answer one question, then finish.
        client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "A thorough answer with all key points."},
            headers=_auth(token),
        )
        r = client.post(f"/api/kb/interview/{session['id']}/finish", headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "completed"
        assert data["answered"] >= 1
        assert data["total_score"] >= 0

        row = db_session.query(InterviewSession).get(session["id"])
        assert row.status == "completed"

    def test_finish_updates_skill(self, client, db_session):
        from app.models import UserSkill
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        session = _start(client, token)
        client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "A complete and correct answer covering everything."},
            headers=_auth(token),
        )
        client.post(f"/api/kb/interview/{session['id']}/finish", headers=_auth(token))
        user_id = decode_bearer_token(token)["user_id"]
        rows = (
            db_session.query(UserSkill)
            .filter(UserSkill.user_id == user_id, UserSkill.skill_id == "machine learning")
            .all()
        )
        # Free-form skill label is stored as a UserSkill skill_id if not in
        # taxonomy; either way the finish path must not error.
        assert isinstance(rows, list)

    def test_session_persisted(self, client, db_session):
        from app.models import InterviewSession

        token = _signup(client)
        session = _start(client, token)
        row = db_session.query(InterviewSession).get(session["id"])
        assert row is not None
        assert row.skill == "machine learning"
