"""Idea 66 — advanced answer grading tests.

Covers the ``mode=advanced`` grade-answer path: rubric assembly from the
topic's chunks, partial-credit scoring (not binary), the structured feedback
shape (score/strengths/misconceptions/action_items), learning-event logging,
mock-LLM grading, deterministic keyword-overlap fallback, and backward
compatibility of the basic mode.
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


def _signup(client, uname="grd-user", email="grd@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Grd", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _first_topic(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topic = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"][0]
    return profile, topic


class TestAdvancedMode:
    def test_structured_shape_fallback(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            "/api/ai/grade-answer",
            json={
                "question": "What is linear regression?",
                "expected": "Linear regression models the relationship between inputs and a continuous target.",
                "answer": "Regression finds relationships between variables.",
                "mode": "advanced",
                "topic_id": topic["id"],
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mode"] == "advanced"
        assert isinstance(data["score"], int)
        assert 0 <= data["score"] <= 100
        assert isinstance(data["strengths"], list)
        assert isinstance(data["misconceptions"], list)
        assert isinstance(data["action_items"], list)
        assert data["ai_used"] is False

    def test_partial_credit_not_binary(self, client):
        # Keyword-overlap fallback: a half-covering answer gets a mid score,
        # not an all-or-nothing 0/100.
        token = _signup(client)
        _ = token
        r = client.post(
            "/api/ai/grade-answer",
            json={
                "question": "Q",
                "expected": "alpha beta gamma delta",
                "answer": "alpha beta",
                "mode": "advanced",
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        score = r.json()["score"]
        assert 0 < score < 100

    def test_full_overlap_scores_high(self, client):
        token = _signup(client)
        r = client.post(
            "/api/ai/grade-answer",
            json={
                "question": "Q",
                "expected": "alpha beta gamma",
                "answer": "alpha beta gamma",
                "mode": "advanced",
            },
            headers=_auth(token),
        )
        assert r.json()["score"] == 100

    def test_mock_llm_grading(self, client, monkeypatch):
        token = _signup(client)
        _, topic = _first_topic(client, token)

        def fake_generate_json(prompt, **kwargs):
            return {
                "score": 82,
                "strengths": ["Good intuition", "Mentions the key idea"],
                "misconceptions": ["Confuses target types"],
                "action_items": ["Re-read the regression chapter"],
            }

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        r = client.post(
            "/api/ai/grade-answer",
            json={
                "question": "What is linear regression?",
                "expected": "Expected answer here.",
                "answer": "A student answer.",
                "mode": "advanced",
                "topic_id": topic["id"],
            },
            headers=_auth(token),
        )
        data = r.json()
        assert data["score"] == 82
        assert data["strengths"] == ["Good intuition", "Mentions the key idea"]
        assert data["ai_used"] is True


class TestEvents:
    def test_grade_persists_learning_event(self, client, db_session):
        from app.models import LearningEvent
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topic = _first_topic(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        client.post(
            "/api/ai/grade-answer",
            json={
                "question": "What is gradient descent?",
                "expected": "Gradient descent iteratively minimizes the loss.",
                "answer": "It minimizes loss by following the gradient.",
                "mode": "advanced",
                "topic_id": topic["id"],
            },
            headers=_auth(token),
        )
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.event_type == "grade")
            .all()
        )
        assert len(events) == 1
        assert 0.0 <= events[0].value <= 1.0


class TestBasicBackwardCompat:
    def test_basic_mode_shape_unchanged(self, client):
        token = _signup(client)
        r = client.post(
            "/api/ai/grade-answer",
            json={
                "question": "Q",
                "expected": "The correct answer.",
                "answer": "The correct answer.",
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["correct"] is True
        assert "explanation" in r.json()
