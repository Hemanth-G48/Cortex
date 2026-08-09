"""Idea 56 — attendance tests.

Upsert marking per user+subject+date, history + per-subject stats (percent,
streaks), analytics rollup, falling-pattern alerts (N consecutive misses →
Notification), per-user isolation.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import Notification

SYLLABUS = """\
# Machine Learning

Fall 2026

## Unit 1: Foundations
- Linear algebra review
- Probability review
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="att-user", email="att@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Att", "username": uname, "email": email,
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
    return confirmed.json()["profile"]["curriculum_subject_id"]


def _mark(client, token, subject_id, day_offset, present=True):
    d = (date.today() - timedelta(days=day_offset)).isoformat()
    return client.post(
        "/api/attendance",
        json={"subject_id": subject_id, "class_date": d, "present": present},
        headers=_auth(token),
    )


class TestMark:
    def test_mark_and_upsert(self, client):
        token = _signup(client)
        subject_id = _confirmed(client, token)
        r = _mark(client, token, subject_id, 0)
        assert r.status_code == 200
        assert r.json()["attendance"]["present"] is True
        # Same day flip → upsert (still one row).
        r = _mark(client, token, subject_id, 0, present=False)
        assert r.json()["attendance"]["present"] is False
        hist = client.get(
            f"/api/subjects/{subject_id}/attendance", headers=_auth(token)
        ).json()
        assert len(hist["items"]) == 1

    def test_stats_percent_and_streak(self, client):
        token = _signup(client)
        subject_id = _confirmed(client, token)
        _mark(client, token, subject_id, 2)
        _mark(client, token, subject_id, 1)
        _mark(client, token, subject_id, 0, present=False)
        hist = client.get(
            f"/api/subjects/{subject_id}/attendance", headers=_auth(token)
        ).json()
        stats = hist["stats"]
        assert stats["total"] == 3
        assert stats["present"] == 2
        assert stats["percent"] == round(2 / 3 * 100, 1)

    def test_current_streak_counts_consecutive_present(self, client):
        token = _signup(client)
        subject_id = _confirmed(client, token)
        _mark(client, token, subject_id, 1)
        _mark(client, token, subject_id, 0)
        hist = client.get(
            f"/api/subjects/{subject_id}/attendance", headers=_auth(token)
        ).json()
        assert hist["stats"]["current_streak"] == 2

    def test_analytics_rolls_up_per_subject(self, client):
        token = _signup(client)
        subject_id = _confirmed(client, token)
        _mark(client, token, subject_id, 0)
        _mark(client, token, subject_id, 1, present=False)
        r = client.get("/api/attendance/analytics", headers=_auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["total_classes"] == 2
        assert data["present"] == 1
        assert str(subject_id) in data["subjects"]


class TestFallingPattern:
    def test_alert_after_consecutive_misses(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.KB_ATTENDANCE_ALERT_STREAK", 2)
        token = _signup(client)
        subject_id = _confirmed(client, token)
        r1 = _mark(client, token, subject_id, 0, present=False)
        r2 = _mark(client, token, subject_id, 1, present=False)
        # Alert fires on the second consecutive miss.
        assert r1.json()["alert"] is None
        assert r2.json()["alert"] == {"kind": "attendance_alert", "subject_id": subject_id}
        notifications = db_session.query(Notification).filter(
            Notification.kind == "attendance_alert"
        ).all()
        assert len(notifications) == 1
        assert "missed" in notifications[0].body

    def test_no_alert_when_present_breaks_run(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.KB_ATTENDANCE_ALERT_STREAK", 2)
        token = _signup(client)
        subject_id = _confirmed(client, token)
        _mark(client, token, subject_id, 0, present=False)
        r = _mark(client, token, subject_id, 1, present=True)
        assert r.json()["alert"] is None
        assert (
            db_session.query(Notification)
            .filter(Notification.kind == "attendance_alert")
            .count()
            == 0
        )


class TestIsolation:
    def test_attendance_is_per_user(self, client):
        token_a = _signup(client, "att-a", "atta@test.com")
        token_b = _signup(client, "att-b", "attb@test.com")
        subject_id = _confirmed(client, token_a)
        _mark(client, token_a, subject_id, 0)
        hist_b = client.get(
            f"/api/subjects/{subject_id}/attendance", headers=_auth(token_b)
        ).json()
        assert hist_b["items"] == []
        assert hist_b["stats"]["total"] == 0
