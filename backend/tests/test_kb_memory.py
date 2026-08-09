"""Idea 79 — long-term learning memory store tests.

Covers bump accumulation/exposure, decay math (exponential half-life),
event-driven updates via bump_from_topic, per-user isolation, the
strengths/weaknesses + anchors seams, and the GET /api/kb/memory endpoint.
"""
from __future__ import annotations

import pytest
from datetime import timedelta

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


def _signup(client, uname="mem-user", email="mem@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mem", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestBump:
    def test_bump_creates_and_accumulates(self, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.kb.memory import bump

        concept = KbConcept(user_id=1, canonical_name="neural nets")
        db_session.add(concept)
        db_session.commit()

        bump(db_session, 1, [concept.id], delta=0.2, source="quiz")
        bump(db_session, 1, [concept.id], delta=0.3, source="quiz")
        db_session.commit()

        row = db_session.query(UserMemory).filter(
            UserMemory.user_id == 1, UserMemory.concept_id == concept.id
        ).first()
        assert row is not None
        assert abs(row.strength - 0.5) < 1e-6
        assert row.exposure_count == 2
        assert row.last_seen is not None
        assert row.source == "quiz"

    def test_bump_clamps_strength(self, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.kb.memory import bump

        concept = KbConcept(user_id=1, canonical_name="linear regression")
        db_session.add(concept)
        db_session.commit()
        bump(db_session, 1, [concept.id], delta=5.0)
        db_session.commit()
        row = db_session.query(UserMemory).filter(UserMemory.user_id == 1).first()
        assert row.strength == 1.0

    def test_bump_negative_delta_is_noop(self, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.kb.memory import bump

        concept = KbConcept(user_id=1, canonical_name="statistics")
        db_session.add(concept)
        db_session.commit()
        bump(db_session, 1, [concept.id], delta=0.5, source="practice")
        bump(db_session, 1, [concept.id], delta=-1.0, source="practice")
        db_session.commit()
        row = db_session.query(UserMemory).filter(UserMemory.user_id == 1).first()
        assert row.strength == 0.5  # never erased by a bad answer


class TestDecay:
    def test_half_life_math(self, db_session, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.kb.memory import bump, decay

        monkeypatch.setattr("app.config.settings.KB_MEMORY_HALF_LIFE_DAYS", 30)
        concept = KbConcept(user_id=1, canonical_name="optimization")
        db_session.add(concept)
        db_session.commit()
        bump(db_session, 1, [concept.id], delta=1.0)
        db_session.commit()

        now = utcnow()
        row = db_session.query(UserMemory).filter(UserMemory.user_id == 1).first()
        row.last_seen = now - timedelta(days=30)  # exactly one half-life ago
        db_session.commit()

        touched = decay(db_session, 1, now=now)
        assert touched == 1
        row = db_session.query(UserMemory).filter(UserMemory.user_id == 1).first()
        assert abs(row.strength - 0.5) < 0.01

    def test_zero_strength_stays_zero(self, db_session, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.kb.memory import decay

        monkeypatch.setattr("app.config.settings.KB_MEMORY_HALF_LIFE_DAYS", 30)
        concept = KbConcept(user_id=1, canonical_name="calculus")
        db_session.add(concept)
        db_session.commit()
        now = utcnow()
        db_session.add(UserMemory(user_id=1, concept_id=concept.id, strength=0.0,
                                  last_seen=now - timedelta(days=100)))
        db_session.commit()
        assert decay(db_session, 1, now=now) == 0


class TestEventDriven:
    def test_bump_from_topic_matches_concepts(self, client, db_session):
        from app.models import KbConcept, Topic, UserMemory
        from app.services.kb.memory import bump_from_topic
        from app.services.security import decode_bearer_token

        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
        profile = r.json()["profile"]
        client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        user_id = decode_bearer_token(token)["user_id"]

        concept = KbConcept(user_id=user_id, canonical_name="Linear regression")
        db_session.add(concept)
        db_session.commit()
        topic = db_session.query(Topic).filter(Topic.user_id == user_id, Topic.name == "Linear regression").first()
        assert topic is not None

        touched = bump_from_topic(db_session, user_id, topic.id, delta=0.1, source="revision")
        db_session.commit()
        assert concept.id in touched
        row = db_session.query(UserMemory).filter(
            UserMemory.user_id == user_id, UserMemory.concept_id == concept.id
        ).first()
        assert row is not None
        assert row.strength >= 0.1
        assert row.source == "revision"

    def test_bump_from_unknown_topic_noop(self, db_session):
        from app.services.kb.memory import bump_from_topic

        assert bump_from_topic(db_session, 1, 999999, delta=0.1) == []


class TestSeams:
    def test_strengths_weaknesses_and_anchors(self, db_session, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.kb.memory import anchors, strengths_weaknesses

        monkeypatch.setattr("app.config.settings.KB_MEMORY_ANCHOR_MIN", 0.4)
        c_strong = KbConcept(user_id=1, canonical_name="probability")
        c_weak = KbConcept(user_id=1, canonical_name="calculus")
        db_session.add_all([c_strong, c_weak])
        db_session.flush()
        db_session.add_all([
            UserMemory(user_id=1, concept_id=c_strong.id, strength=0.9, exposure_count=5, last_seen=utcnow()),
            UserMemory(user_id=1, concept_id=c_weak.id, strength=0.2, exposure_count=1, last_seen=utcnow()),
        ])
        db_session.commit()

        sw = strengths_weaknesses(db_session, 1)
        assert sw["strengths"] == ["probability"]
        assert sw["weaknesses"] == ["calculus"]
        assert anchors(db_session, 1) == ["probability"]


class TestEndpoint:
    def test_get_memory_returns_snapshot(self, client, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="gradient descent")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.7,
                                  exposure_count=4, last_seen=utcnow()))
        db_session.commit()

        r = client.get("/api/kb/memory", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["concept"] == "gradient descent"
        assert items[0]["strength"] == 0.7

    def test_memory_endpoints_are_per_user(self, client, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.security import decode_bearer_token

        t_a = _signup(client, "mem-a", "mema@test.com")
        t_b = _signup(client, "mem-b", "memb@test.com")
        user_a = decode_bearer_token(t_a)["user_id"]
        concept = KbConcept(user_id=user_a, canonical_name="physics")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_a, concept_id=concept.id, strength=0.8))
        db_session.commit()

        assert len(client.get("/api/kb/memory", headers=_auth(t_b)).json()["items"]) == 0
        assert len(client.get("/api/kb/memory", headers=_auth(t_a)).json()["items"]) == 1

    def test_bump_and_decay_endpoints(self, client, db_session):
        from app.models import KbConcept
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="linear algebra")
        db_session.add(concept)
        db_session.commit()

        r = client.post("/api/kb/memory/bump", json={"concept_ids": [concept.id], "delta": 0.5, "source": "quiz"},
                        headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["touched"] == [concept.id]

        items = client.get("/api/kb/memory", headers=_auth(token)).json()["items"]
        assert items[0]["strength"] == 0.5

        d = client.post("/api/kb/memory/decay", headers=_auth(token))
        assert d.status_code == 200, d.text
