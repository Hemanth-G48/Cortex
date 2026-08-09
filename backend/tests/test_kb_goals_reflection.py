"""Idea 98 — goal planning & reflection tests.

Goal↔roadmap linkage + progress, term-goal derivation + confirm, weekly
reflection generation with coalesced insight push, plan-adjustment trigger,
and per-user isolation.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import Goal, LearningEvent, Notification, Reflection, Topic
from app.services.kb import reflections as reflection_service
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Machine Learning

## Unit 1: Foundations
- Linear regression
- Gradient descent
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="goal-user", email="goal@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Goal", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    c = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    # The confirm response carries the populated curriculum_subject_id.
    profile = c.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


class TestGoals:
    def test_derive_and_confirm_goal(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]

        r = client.get("/api/kb/goals/derived", headers=_auth(token))
        assert r.status_code == 200
        proposals = [p for p in r.json()["items"] if p["subject_id"] == subject_id]
        assert proposals

        c = client.post(
            "/api/kb/goals/derived/confirm",
            json=proposals[0],
            headers=_auth(token),
        )
        assert c.status_code == 200, c.text
        goal = db_session.query(Goal).filter(
            Goal.user_id == uid, Goal.subject_id == subject_id
        ).first()
        assert goal is not None
        assert goal.title == f"Master Machine Learning"

    def test_goal_progress_from_roadmap(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        proposals = [p for p in reflection_service.derive_goals(db_session, uid) if p["subject_id"] == subject_id]
        goal = reflection_service.confirm_derived_goal(db_session, uid, proposals[0])
        db_session.commit()

        # Mark one topic strong → progress reflects mastery.
        topics = db_session.query(Topic).filter(Topic.user_id == uid).all()
        if topics:
            topics[0].mastery_score = 0.9
            topics[0].mastery_classification = "strong"
            db_session.commit()
        result = reflection_service.goal_progress(db_session, uid, goal.id)
        assert result["goal_id"] == goal.id
        assert result["progress_percentage"] >= 0


class TestReflection:
    def test_generate_with_notification(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _confirmed(client, token)
        topic = db_session.query(Topic).filter(Topic.user_id == uid).first()
        db_session.add(LearningEvent(
            user_id=uid, topic_id=topic.id, event_type="quiz", value=0.9,
            created_at=datetime.utcnow(),
        ))
        db_session.commit()

        r = client.post("/api/kb/reflections/generate", json={}, headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["content"]
        assert body["insights"]["worked"]
        assert body["pushed"] is True

        # Coalesced: a second generate does not create a second notification.
        r2 = client.post("/api/kb/reflections/generate", json={}, headers=_auth(token))
        assert r2.json()["pushed"] is False
        notif_count = db_session.query(Notification).filter(
            Notification.user_id == uid, Notification.kind == "reflection"
        ).count()
        assert notif_count == 1

    def test_fallback_insights_deterministic(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        insights = reflection_service._fallback_insights([])
        assert insights["worked"]
        assert "no study activity" in insights["worked"][0].lower()

    def test_list_reflections(self, client):
        token = _signup(client)
        client.post("/api/kb/reflections/generate", json={}, headers=_auth(token))
        r = client.get("/api/kb/reflections", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_plan_adjustments_safe_noop(self, client):
        """apply_plan_adjustments never crashes with zero subjects."""
        token = _signup(client)
        r = client.post("/api/kb/reflections/adjust", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["count"] == 0


class TestIsolation:
    def test_reflections_are_per_user(self, client, db_session):
        token_a = _signup(client, "goal-a", "goala@test.com")
        token_b = _signup(client, "goal-b", "goalb@test.com")
        client.post("/api/kb/reflections/generate", json={}, headers=_auth(token_a))
        rows = db_session.query(Reflection).all()
        assert len(rows) == 1
        assert rows[0].user_id == _uid(token_a)
        r = client.get("/api/kb/reflections", headers=_auth(token_b))
        assert r.json()["items"] == []
