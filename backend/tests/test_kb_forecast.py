"""Idea 99 — trajectory forecasting tests.

EWMA math, linear model option, exam-readiness scoring, at-risk flags,
coalesced early-warning alerts, and per-user isolation.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.models import Exam, LearningEvent, Notification, Topic
from app.services.kb import forecast as forecast_service
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Statistics

## Unit 1: Foundations
- Probability
- Distributions
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="fore-user", email="fore@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Fore", "username": uname, "email": email,
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


class TestSeries:
    def test_ewma_math(self):
        values = [0.2, 0.4, 0.6, 0.8, 1.0]
        smoothed = forecast_service.ewma_series(values, alpha=1.0)
        # alpha=1 → exact copy.
        assert smoothed == [round(v, 4) for v in values]
        smoothed2 = forecast_service.ewma_series(values, alpha=0.0)
        # alpha=0 → first value repeats.
        assert smoothed2 == [0.2, 0.2, 0.2, 0.2, 0.2]

    def test_linear_forecast_single(self):
        assert forecast_service.linear_forecast([0.5]) == 0.5
        # Increasing series → forecast above the last value.
        assert forecast_service.linear_forecast([0.1, 0.2, 0.3, 0.4]) > 0.4

    def test_series_builds_from_events(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        topic = db_session.query(Topic).filter(Topic.user_id == uid).first()
        db_session.add(LearningEvent(
            user_id=uid, topic_id=topic.id, event_type="quiz", value=0.6,
            created_at=datetime.utcnow() - timedelta(days=2),
        ))
        db_session.add(LearningEvent(
            user_id=uid, topic_id=topic.id, event_type="quiz", value=0.9,
            created_at=datetime.utcnow(),
        ))
        db_session.commit()
        traj = forecast_service.trajectory(db_session, uid, subject_id)
        assert traj["series_points"] == 2
        assert traj["points"]
        assert traj["forecast"] > 0


class TestReadiness:
    def test_exam_decays_readiness(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        db_session.add(Exam(
            title="Stats Final", course_id=subject_id,
            date=date.today() + timedelta(days=3),
        ))
        db_session.commit()
        base = forecast_service._readiness(0.8, None)
        near_exam = forecast_service._readiness(0.8, 3)
        assert near_exam < base

    def test_at_risk_threshold(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_FORECAST_RISK_THRESHOLD", 0.5)
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        # No events → forecast 0 → at risk.
        traj = forecast_service.trajectory(db_session, uid, subject_id)
        assert traj["at_risk"] is True
        assert traj["readiness"] < 0.5

    def test_forecast_endpoint(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        r = client.get(f"/api/kb/forecast/{subject_id}", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert "points" in body
        assert "readiness" in body
        assert "at_risk" in body


class TestAlerts:
    def test_alert_fires_once(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        first = forecast_service.check_at_risk(db_session, uid, subject_id)
        assert first["at_risk"] is True
        assert first["alerted"] is True
        second = forecast_service.check_at_risk(db_session, uid, subject_id)
        assert second["alerted"] is False
        count = db_session.query(Notification).filter(
            Notification.user_id == uid,
            Notification.kind == "forecast",
            Notification.ref_type == f"at-risk:{subject_id}",
        ).count()
        assert count == 1

    def test_scan_sweeps_all_subjects(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _confirmed(client, token)
        result = forecast_service.run(db_session, uid)
        assert result["processed"] >= 1


class TestIsolation:
    def test_forecast_is_per_user(self, client, db_session):
        uid_a = _uid(_signup(client, "fore-a", "forea@test.com"))
        uid_b = _uid(_signup(client, "fore-b", "foreb@test.com"))
        # Only A has a subject; A's sweep touches nothing of B's.
        forecast_service.run(db_session, uid_a)
        notifications = db_session.query(Notification).all()
        assert all(n.user_id == uid_a for n in notifications)
