"""Idea 68 — explain-my-mistake analysis tests.

Covers the mistake walkthrough endpoint: divergence detection (LLM mocked or
keyword-diff fallback), recommended note to re-read + concept to review,
revision-task creation (scheduled review), learning-event logging, persisted
analysis, and per-user isolation.
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


def _signup(client, uname="mst-user", email="mst@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mst", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _approved_question(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topic = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"][0]
    q = client.post(
        "/api/kb/practice/generate",
        json={"topic_id": topic["id"], "count": 1, "difficulty": "M"},
        headers=_auth(token),
    ).json()["items"][0]
    client.post(f"/api/kb/practice/{q['id']}/approve", headers=_auth(token))
    return q


class TestAnalyze:
    def test_fallback_analysis_shape(self, client):
        token = _signup(client)
        q = _approved_question(client, token)
        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "a partial answer"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["analysis_id"] > 0
        assert data["divergence"]
        assert isinstance(data["missed_points"], list)
        assert data["recommendation"]
        assert data["ai_used"] is False

    def test_mock_llm_analysis(self, client, monkeypatch):
        token = _signup(client)
        q = _approved_question(client, token)

        def fake_generate_json(prompt, **kwargs):
            return {
                "divergence": "You skipped the step of normalizing the inputs.",
                "missed_points": ["normalization", "learning rate"],
                "recommendation": "Re-read the gradient descent note.",
            }

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "wrong answer"},
            headers=_auth(token),
        )
        data = r.json()
        assert data["ai_used"] is True
        assert "normalizing" in data["divergence"]
        assert data["missed_points"] == ["normalization", "learning rate"]

    def test_concept_recommendation(self, client, db_session):
        from app.models import KbConcept
        from app.services.security import decode_bearer_token

        token = _signup(client)
        q = _approved_question(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        # The fallback question text embeds the topic name (first topic is the
        # syllabus's "Linear algebra review") → a concept matching that name
        # is recommended.
        db_session.add(KbConcept(
            user_id=user_id, canonical_name="Linear Algebra",
            aliases="[]", definition="Study of vector spaces and matrices.",
        ))
        db_session.commit()

        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "wrong"},
            headers=_auth(token),
        )
        data = r.json()
        assert data["recommended_concept_id"] is not None

    def test_revision_task_created(self, client, db_session):
        from app.models import RevisionSchedule
        from app.services.security import decode_bearer_token

        token = _signup(client)
        q = _approved_question(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "wrong"},
            headers=_auth(token),
        )
        assert r.json()["revision_task_created"] is True
        rows = (
            db_session.query(RevisionSchedule)
            .filter(RevisionSchedule.user_id == user_id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].due_date is not None  # due today

    def test_mistake_event_logged_and_persisted(self, client, db_session):
        from app.models import LearningEvent, MistakeAnalysis
        from app.services.security import decode_bearer_token

        token = _signup(client)
        q = _approved_question(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "wrong"},
            headers=_auth(token),
        )
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.event_type == "mistake")
            .all()
        )
        assert len(events) >= 1
        analyses = (
            db_session.query(MistakeAnalysis)
            .filter(MistakeAnalysis.user_id == user_id)
            .all()
        )
        assert len(analyses) == 1
        assert analyses[0].walkthrough

    def test_unknown_question_404(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": 9999, "student_answer": "x"},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_isolation(self, client):
        t_a = _signup(client, "mst-a", "msta@test.com")
        t_b = _signup(client, "mst-b", "mstb@test.com")
        q = _approved_question(client, t_a)
        r = client.post(
            "/api/kb/practice/mistake-analysis",
            json={"question_id": q["id"], "student_answer": "x"},
            headers=_auth(t_b),
        )
        assert r.status_code == 404
