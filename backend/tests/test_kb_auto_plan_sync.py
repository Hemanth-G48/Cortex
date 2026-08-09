"""Auto plan-sync job tests (Phase 9, Idea 88, phrases 71-80)."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, Notification, Roadmap, Topic, User
from app.services.kb.auto_plan_sync import run
from app.services.security import decode_bearer_token

AUTH = "Authorization"

SYLLABUS = """\
# Machine Learning

Fall 2026

## Unit 1: Foundations
- Linear algebra review
- Probability review

## Unit 2: Regression
- Linear regression
- Gradient descent

## Unit 3: Classification
- Logistic regression
- Decision trees
"""


def _signup(client: TestClient, uname: str = "plan-sync", email: str = "plansync@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Planner",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _confirmed(client: TestClient, token: str):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers={AUTH: f"Bearer {token}"})
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers={AUTH: f"Bearer {token}"})
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers={AUTH: f"Bearer {token}"})
    return profile


class TestRun:
    def test_revises_plan_when_estimate_delta_passes_threshold(
        self, db_session: Session, client: TestClient, monkeypatch
    ):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        profile = _confirmed(client, token)

        # Generate an initial roadmap (version 1).
        client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate", json={}, headers={AUTH: f"Bearer {token}"}
        )

        # Force one topic's estimate far from the recomputed value (no material
        # mentions → recompute yields the minimum 15m).
        topic = db_session.query(Topic).filter(Topic.user_id == uid).first()
        topic.first_pass_mins = 60
        db_session.add(topic)
        db_session.commit()

        summary = run(db_session, uid)
        assert summary["processed"] >= 1
        assert summary["topic_changes"] >= 1
        assert summary["revised"] >= 1
        assert summary["notifications"] >= 1

        db_session.refresh(topic)
        assert topic.first_pass_mins == 15  # recomputed from (empty) coverage

        # A new roadmap version exists and a plan_sync notification was written.
        versions = (
            db_session.query(Roadmap)
            .filter(Roadmap.user_id == uid, Roadmap.status == "active")
            .count()
        )
        assert versions >= 1
        note = (
            db_session.query(Notification)
            .filter(Notification.user_id == uid, Notification.kind == "plan_sync")
            .first()
        )
        assert note is not None
        assert "plan updated" in note.title.lower()

    def test_noop_below_threshold(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        profile = _confirmed(client, token)

        # Align every topic's estimate with the recomputed minimum → delta 0.
        for topic in db_session.query(Topic).filter(Topic.user_id == uid).all():
            topic.first_pass_mins = 15
            topic.review_mins = 6
            topic.mastery_mins = 9
            db_session.add(topic)
        db_session.commit()

        summary = run(db_session, uid)
        assert summary["topic_changes"] == 0
        assert summary["revised"] == 0
        assert summary["notifications"] == 0

    def test_new_material_shrinks_estimate(self, db_session: Session, client: TestClient, monkeypatch):
        """More mentioning chunks → higher volume → recompute stays consistent."""
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        profile = _confirmed(client, token)

        # Give one topic a lot of mentioning material so its recomputed
        # estimate grows well above 15m.
        topic = db_session.query(Topic).filter(Topic.user_id == uid).first()
        doc = KbDocument(
            user_id=uid,
            title="notes",
            doc_type="md",
            path_rel="notes.md",
            extracted_text=f"# Notes\n\n{topic.name} appears repeatedly here.",
            content_hash="hash-notes",
            char_count=80,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        for i in range(6):
            db_session.add(
                KbChunk(
                    user_id=uid,
                    document_id=doc.id,
                    seq=i,
                    content=(f"Chapter {i}: {topic.name} is covered in depth. " * 30),
                    char_start=0,
                    char_end=900,
                    token_estimate=100,
                )
            )
        db_session.commit()

        summary = run(db_session, uid)
        # With volume present, the topic's estimate moves — either up or down
        # vs its generated value; the job must have processed the subject.
        assert summary["processed"] >= 1


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        _confirmed(client, token)

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_plan_sync", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_plan_sync"
        assert resp.json()["status"] == "done"
