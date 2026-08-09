"""Idea 95 — context-aware responses tests.

Bundle assembly (active subject, exams, recent topics), user override,
prompt-block injection, and per-user privacy.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.models import Exam, LearningEvent, Topic
from app.services.kb import context as context_service
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Data Structures

## Unit 1: Foundations
- Arrays
- Linked lists
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="ctx-user", email="ctx@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Ctx", "username": uname, "email": email,
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


class TestBundle:
    def test_bundle_assembles(self, client, db_session):
        from app.models import Course

        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        # Upcoming exam for the subject. Exams resolve through the Course row
        # (Exam.course_id → Course.curriculum_subject_id), so a linked course
        # must exist for the exam to surface in the bundle.
        course = Course(
            user_id=uid, title="Data Structures",
            curriculum_subject_id=subject_id,
        )
        db_session.add(course)
        db_session.flush()
        db_session.add(Exam(
            title="DS Midterm", course_id=course.id,
            date=date.today() + timedelta(days=5),
        ))
        db_session.commit()

        bundle = context_service.build_bundle(db_session, uid)
        assert bundle["active_subject"] is not None
        assert bundle["active_subject"]["subject_id"] == subject_id
        assert bundle["upcoming_exams"]
        assert bundle["upcoming_exams"][0]["days_until"] == 5
        assert bundle["session_length_mins"] > 0
        assert "memory" in bundle

    def test_recent_topics_from_events(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        profile = _confirmed(client, token)
        subject_id = profile["curriculum_subject_id"]
        topic = db_session.query(Topic).filter(
            Topic.user_id == uid, Topic.subject_id == subject_id
        ).first()
        db_session.add(LearningEvent(
            user_id=uid, topic_id=topic.id, event_type="quiz", value=0.8,
            created_at=datetime.utcnow(),
        ))
        db_session.commit()
        bundle = context_service.build_bundle(db_session, uid)
        assert any(t["topic_id"] == topic.id for t in bundle["recent_topics"])

    def test_prompt_block(self, client, db_session):
        token = _signup(client)
        _confirmed(client, token)
        bundle = context_service.build_bundle(db_session, _uid(token))
        block = context_service.context_prompt_block(bundle)
        assert "active subject" in block
        assert "Data Structures" in block


class TestOverride:
    def test_override_active_subject(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        r = client.put(
            "/api/kb/context",
            json={"active_subject_id": 42, "active_subject_name": "DSA"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["saved"]["active_subject_id"] == 42
        bundle = context_service.build_bundle(db_session, uid)
        assert bundle["active_subject"]["subject_name"] == "DSA"

    def test_get_context_endpoint(self, client):
        token = _signup(client)
        r = client.get("/api/kb/context", headers=_auth(token))
        assert r.status_code == 200
        assert "active_subject" in r.json()
        assert "upcoming_exams" in r.json()


class TestIsolation:
    def test_override_is_per_user(self, client, db_session):
        token_a = _signup(client, "ctx-a", "ctxa@test.com")
        token_b = _signup(client, "ctx-b", "ctxb@test.com")
        client.put("/api/kb/context", json={"active_subject_id": 7, "active_subject_name": "Algorithms"}, headers=_auth(token_a))
        bundle_b = context_service.build_bundle(db_session, _uid(token_b))
        assert bundle_b["override"] == {}
