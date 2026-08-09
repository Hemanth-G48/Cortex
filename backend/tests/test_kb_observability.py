"""Idea 100 — observability tests.

Every AI surface logs to ai_logs, feedback aggregation, the weekly report
payload, A/B prompt versioning, and the admin/teacher guard on the dashboard.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models import AiLog, PromptVersion
from app.services.kb import ai_log as ai_log_service
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="obs-user", email="obs@test.com", role="student", secret=None):
    payload = {"name": "Obs", "username": uname, "email": email,
               "password": "pass123", "role": role}
    if secret:
        payload["teacher_secret"] = secret
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestLogging:
    def test_log_event_writes_row(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        row = ai_log_service.log_event(
            db_session, uid,
            feature="tutor",
            request="what is entropy?",
            response="Entropy measures disorder [source: a.md]",
            latency_ms=120,
            tokens=300,
            retrieval={"mode": "hybrid", "chunk_ids": [1, 2]},
        )
        db_session.commit()
        assert row is not None
        stored = db_session.query(AiLog).filter(AiLog.user_id == uid).first()
        assert stored.feature == "tutor"
        assert stored.latency_ms == 120
        assert stored.cost_estimate > 0

    def test_never_raises_when_disabled(self, client, db_session, monkeypatch):
        token = _signup(client)
        monkeypatch.setattr("app.config.settings.KB_AI_LOG_ENABLED", False)
        row = ai_log_service.log_event(db_session, _uid(token), feature="tutor", request="hi")
        assert row is None

    def test_feedback_aggregation(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        for fb in (1, 1, -1, 0):
            ai_log_service.log_event(
                db_session, uid, feature="tutor", request="q", response="a", feedback=fb
            )
        db_session.commit()
        agg = ai_log_service.aggregate(db_session, uid)
        assert agg["total"] == 4
        assert agg["feedback"] == {"positive": 2, "negative": 1, "neutral": 1}
        assert "tutor" in agg["by_feature"]

    def test_set_feedback_endpoint(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        row = ai_log_service.log_event(db_session, uid, feature="tutor", request="q")
        db_session.commit()
        r = client.post(
            f"/api/kb/observability/{row.id}/feedback",
            json={"feedback": 1},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["feedback"] == 1


class TestWeeklyReport:
    def test_report_aggregates(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        ai_log_service.log_event(
            db_session, uid, feature="grading", request="g", response="r",
            latency_ms=50, faithfulness_score=0.9,
        )
        ai_log_service.log_event(
            db_session, uid, feature="grading", request="g2", response="r2",
            latency_ms=150, faithfulness_score=0.2,
        )
        db_session.commit()
        report = ai_log_service.weekly_report(db_session, uid, week_start=date.today())
        assert report["aggregate"]["total"] == 2
        assert report["aggregate"]["p95_latency_ms"] == 150
        assert report["top_failures"] == 1


class TestPromptVersioning:
    def test_get_prompt_creates_v1(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        template, version = ai_log_service.get_prompt(db_session, "tutor", "v1 template")
        assert template == "v1 template"
        assert version == 1
        db_session.commit()
        row = db_session.query(PromptVersion).filter(PromptVersion.feature == "tutor").first()
        assert row.version == 1

    def test_pin_prompt_bumps_version(self, client, db_session):
        _signup(client)
        ai_log_service.get_prompt(db_session, "tutor", "v1 template")
        row = ai_log_service.pin_prompt(db_session, "tutor", "v2 template")
        db_session.commit()
        assert row.version == 2
        assert row.is_active == 1
        template, version = ai_log_service.get_prompt(db_session, "tutor", "x")
        assert version == 2
        assert template == "v2 template"


class TestGuards:
    def test_student_blocked_from_dashboard(self, client):
        token = _signup(client)
        r = client.get("/api/kb/observability", headers=_auth(token))
        assert r.status_code == 403

    def test_admin_can_view(self, client):
        # Seed admin (id 1) exists; sign up a student is blocked, so mint an
        # admin token directly via the token factory.
        from app.services.security import create_bearer_token

        token = create_bearer_token(1, "admin")
        r = client.get("/api/kb/observability", headers=_auth(token))
        assert r.status_code == 200
        assert "total" in r.json()
