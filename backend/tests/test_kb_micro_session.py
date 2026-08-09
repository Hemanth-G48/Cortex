"""Idea 60 — micro-sessions tests.

Suggested-session factory (Bloom-level practice task, clamped 15–45 min
duration), start → complete lifecycle logging a ``session`` LearningEvent,
one-tap Pomodoro launch, suggested-sessions feed from the recommender,
per-user isolation.
"""
from __future__ import annotations

import pytest

from app.models import LearningEvent, MicroSession, PomodoroSession

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


def _signup(client, uname="mic-user", email="mic@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mic", "username": uname, "email": email,
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


class TestBuildAndStart:
    def test_start_creates_session_with_practice_task(self, client):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        r = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        s = r.json()["session"]
        assert s["status"] == "started"
        assert s["topic_id"] == topics[0]["id"]
        assert s["topic_name"] == topics[0]["name"]
        assert s["practice_task"]
        assert s["duration_mins"] == 25

    def test_duration_out_of_range_422(self, client):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        r = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 999},
            headers=_auth(token),
        )
        assert r.status_code == 422
        r = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 1},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_custom_duration_within_range(self, client):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        r = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 30},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["session"]["duration_mins"] == 30

    def test_unknown_topic_404(self, client):
        token = _signup(client)
        r = client.post("/api/sessions/start", json={"topic_id": 9999}, headers=_auth(token))
        assert r.status_code == 404


class TestComplete:
    def test_complete_logs_learning_event(self, client, db_session):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        s = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 30},
            headers=_auth(token),
        ).json()["session"]
        r = client.post(f"/api/sessions/{s['id']}/complete", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["session"]["status"] == "done"
        assert r.json()["session"]["completed_at"] is not None
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.event_type == "session")
            .all()
        )
        assert len(events) == 1
        assert events[0].topic_id == topics[0]["id"]
        assert events[0].value == 30.0

    def test_complete_unknown_session_404(self, client):
        token = _signup(client)
        assert client.post("/api/sessions/9999/complete", headers=_auth(token)).status_code == 404


class TestPomodoro:
    def test_one_tap_launch(self, client, db_session):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        s = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"], "duration_mins": 25},
            headers=_auth(token),
        ).json()["session"]
        r = client.post(f"/api/sessions/{s['id']}/pomodoro", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["duration_minutes"] == 25
        assert r.json()["ok"] is True
        # Seed data has its own pomodoro rows — filter to the one we launched.
        pomos = (
            db_session.query(PomodoroSession)
            .filter(PomodoroSession.task_description.like(f"%({s['id']})%"))
            .all()
        )
        assert len(pomos) == 1
        assert pomos[0].mode == "Focus"


class TestSuggestedFeed:
    def test_suggested_sessions_from_recommender(self, client):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        r = client.get("/api/sessions/suggested", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items
        for s in items:
            assert s["status"] == "suggested"
            assert s["practice_task"]

    def test_suggested_empty_without_topics(self, client):
        token = _signup(client)
        assert client.get("/api/sessions/suggested", headers=_auth(token)).json()["items"] == []


class TestIsolation:
    def test_sessions_are_per_user(self, client):
        token_a = _signup(client, "mic-a", "mica@test.com")
        token_b = _signup(client, "mic-b", "micb@test.com")
        _, topics = _confirmed(client, token_a)
        s = client.post(
            "/api/sessions/start",
            json={"topic_id": topics[0]["id"]},
            headers=_auth(token_a),
        ).json()["session"]
        assert client.post(f"/api/sessions/{s['id']}/complete", headers=_auth(token_b)).status_code == 404
        assert client.post(f"/api/sessions/{s['id']}/pomodoro", headers=_auth(token_b)).status_code == 404
        # B's suggested feed is empty.
        assert client.get("/api/sessions/suggested", headers=_auth(token_b)).json()["items"] == []
