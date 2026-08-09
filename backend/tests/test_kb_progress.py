"""Idea 57 — progress dashboard tests.

Per-subject progress payload: topic counts, coverage %, hours logged, event
breakdown, quiz accuracy trend, and per-topic mastery map. Empty-subject
progress degrades gracefully.
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


def _signup(client, uname="prog-user", email="prog@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Prog", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    confirmed = client.post(
        f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token)
    )
    profile = confirmed.json()["profile"]  # now carries curriculum_subject_id
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
    return profile, topics


class TestProgressPayload:
    def test_empty_progress(self, client):
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
        profile = r.json()["profile"]
        client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
        # No topics generated yet.
        r = client.get(f"/api/subjects-ai/{profile['id']}/progress", headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["topics_total"] == 0
        assert data["coverage_pct"] == 0.0
        assert data["hours_logged"] == 0.0
        assert data["mastery"] == {}

    def test_counts_and_coverage(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        r = client.get(f"/api/subjects-ai/{profile['id']}/progress", headers=_auth(token))
        data = r.json()
        assert data["topics_total"] == len(topics)
        assert data["topics_unknown"] == len(topics)  # no evidence yet
        assert data["coverage_pct"] == 0.0

    def test_hours_logged_from_sessions(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        # Complete a 25-minute micro-session → hours_logged 25/60.
        r = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 25},
            headers=_auth(token),
        )
        session_id = r.json()["session"]["id"]
        client.post(f"/api/sessions/{session_id}/complete", headers=_auth(token))
        data = client.get(
            f"/api/subjects-ai/{profile['id']}/progress", headers=_auth(token)
        ).json()
        assert data["hours_logged"] == round(25 / 60, 2)
        assert data["events"].get("session") == 1
        # The topic gained evidence.
        assert data["mastery"][str(topics[0]["id"])]["evidence"] == 1

    def test_quiz_trend(self, client, db_session):
        from app.models import LearningEvent
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        profile, topics = _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        for acc in (0.8, 0.9):
            log_event(
                db_session, user_id, event_type="quiz",
                topic_id=topics[0]["id"], value=acc,
            )
        db_session.commit()
        data = client.get(
            f"/api/subjects-ai/{profile['id']}/progress", headers=_auth(token)
        ).json()
        trend = data["quiz_trend"]
        assert len(trend) == 1  # both same day
        assert trend[0]["accuracy"] == round((0.8 + 0.9) / 2, 3)


class TestIsolation:
    def test_progress_is_per_user(self, client):
        token_a = _signup(client, "prog-a", "proga@test.com")
        token_b = _signup(client, "prog-b", "progb@test.com")
        profile, _ = _confirmed(client, token_a)
        assert client.get(
            f"/api/subjects-ai/{profile['id']}/progress", headers=_auth(token_b)
        ).status_code == 404
