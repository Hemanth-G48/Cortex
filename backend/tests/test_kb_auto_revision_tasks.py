"""Auto revision-task job tests (Phase 9, Idea 90, phrases 91-100)."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    CurriculumSubject,
    KbChunk,
    KbDocument,
    MicroSession,
    Reminder,
    RevisionSchedule,
    Task,
    Topic,
    User,
)
from app.services.kb.auto_revision import run
from app.services.kb import utcnow
from app.services.security import decode_bearer_token

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "rev-auto", email: str = "revauto@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Reviser",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_topic(db: Session, user_id: int, name: str = "Gradient descent", *, due_in_days: int = 0) -> Topic:
    subject = CurriculumSubject(
        name="ML",
        code="ML101",
        credits=3,
        program_id=1,
        is_active=True,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    topic = Topic(
        user_id=user_id,
        subject_id=subject.id,
        name=name,
        normalized_name=name.lower(),
        status="confirmed",
        first_pass_mins=60,
        review_mins=24,
        mastery_mins=36,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    db.add(
        RevisionSchedule(
            user_id=user_id,
            topic_id=topic.id,
            interval_days=1,
            ease=2.5,
            repetitions=1,
            due_date=utcnow() - timedelta(days=due_in_days),
        )
    )
    db.commit()
    return topic


class TestRun:
    def test_creates_task_reminder_and_session(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = db_session.query(User).filter(User.email == "revauto@test.com").first().id
        topic = _make_topic(db_session, uid)

        summary = run(db_session, uid)
        assert summary["due"] == 1
        assert summary["tasks_created"] == 1
        assert summary["reminders_created"] == 1
        assert summary["sessions_created"] == 0  # no material → no micro-session

        task = (
            db_session.query(Task)
            .filter(Task.user_id == uid, Task.title == f"Review: {topic.name}")
            .first()
        )
        assert task is not None
        assert task.due_date == date.today()
        assert task.status == "Not started"

        reminder = (
            db_session.query(Reminder).filter(Reminder.title == f"Review: {topic.name}").first()
        )
        assert reminder is not None
        assert reminder.date == date.today()

    def test_idempotent_rerun(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = db_session.query(User).filter(User.email == "revauto@test.com").first().id
        _make_topic(db_session, uid)

        first = run(db_session, uid)
        second = run(db_session, uid)
        assert first["tasks_created"] == 1
        assert second["tasks_created"] == 0  # already materialized

    def test_skips_not_due_revisions(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = db_session.query(User).filter(User.email == "revauto@test.com").first().id
        _make_topic(db_session, uid, due_in_days=-5)  # due in the future

        summary = run(db_session, uid)
        assert summary["due"] == 0
        assert summary["tasks_created"] == 0

    def test_micro_session_when_material_exists(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = db_session.query(User).filter(User.email == "revauto@test.com").first().id
        topic = _make_topic(db_session, uid)
        doc = KbDocument(
            user_id=uid,
            title="notes",
            doc_type="md",
            path_rel="notes.md",
            extracted_text=f"# Notes\n\n{topic.name} in depth.",
            content_hash="hash-n",
            char_count=40,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        db_session.add(
            KbChunk(
                user_id=uid,
                document_id=doc.id,
                seq=0,
                content=f"# Notes\n\n{topic.name} in depth.",
                char_start=0,
                char_end=40,
                token_estimate=10,
            )
        )
        db_session.commit()

        summary = run(db_session, uid)
        assert summary["sessions_created"] == 1
        session = (
            db_session.query(MicroSession)
            .filter(MicroSession.user_id == uid, MicroSession.topic_id == topic.id)
            .first()
        )
        assert session is not None
        assert session.status == "suggested"


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        _make_topic(db_session, uid)

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_revision", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_revision"
        assert resp.json()["status"] == "done"
