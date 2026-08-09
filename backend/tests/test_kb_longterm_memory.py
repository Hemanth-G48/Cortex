"""Idea 92 — long-term memory tests.

Episode appends from learning_events, weekly consolidation (deterministic
fallback), fact folding into user_memory, durable-facts prompt injection,
idempotent re-run, and per-user isolation.
"""
from __future__ import annotations

import pytest

from app.models import EpisodicMemory, KbConcept, LearningEvent, Topic, UserMemory
from app.services.kb import memory_longterm
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _user_id(token) -> int:
    return decode_bearer_token(token)["user_id"]


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


def _make_topic(db, user_id, name="Linear regression"):
    topic = Topic(
        user_id=user_id,
        subject_id=1,
        name=name,
        normalized_name=name.lower(),
        status="confirmed",
        first_pass_mins=60,
    )
    db.add(topic)
    db.flush()
    return topic


def _make_concept(db, user_id, name):
    concept = KbConcept(user_id=user_id, canonical_name=name)
    db.add(concept)
    db.flush()
    return concept


class TestEpisodeAppends:
    def test_appends_from_learning_events(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        topic = _make_topic(db_session, uid)
        db_session.add(LearningEvent(user_id=uid, topic_id=topic.id, event_type="quiz", value=0.8))
        db_session.add(LearningEvent(user_id=uid, topic_id=topic.id, event_type="session", value=25))
        db_session.commit()

        created = memory_longterm.append_episodes(db_session, uid)
        assert created == 2
        episodes = db_session.query(EpisodicMemory).filter(EpisodicMemory.user_id == uid).all()
        assert len(episodes) == 2
        # Deterministic summaries reference the topic.
        assert any("Linear regression" in e.summary for e in episodes)

    def test_append_is_idempotent(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        topic = _make_topic(db_session, uid)
        db_session.add(LearningEvent(user_id=uid, topic_id=topic.id, event_type="revision", value=0.9))
        db_session.commit()
        memory_longterm.append_episodes(db_session, uid)
        second = memory_longterm.append_episodes(db_session, uid)
        assert second == 0


class TestConsolidation:
    def test_fallback_folds_facts_and_marks_covered(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        concept = _make_concept(db_session, uid, "regression")
        topic = _make_topic(db_session, uid)
        db_session.add(LearningEvent(user_id=uid, topic_id=topic.id, event_type="quiz", value=0.8))
        db_session.commit()
        memory_longterm.append_episodes(db_session, uid)

        result = memory_longterm.consolidate(db_session, uid, days=0)
        # Fallback folds topic-attached concepts (no edge → folded may be 0,
        # but the consolidated marker is still written and idempotent).
        assert result["episodes"] == 1
        assert "consolidated" in [
            e.event_type
            for e in db_session.query(EpisodicMemory).filter(EpisodicMemory.user_id == uid).all()
        ]

    def test_re_run_is_idempotent(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        concept = _make_concept(db_session, uid, "bayes")
        topic = _make_topic(db_session, uid)
        db_session.add(LearningEvent(user_id=uid, topic_id=topic.id, event_type="study", value=30))
        db_session.commit()
        memory_longterm.append_episodes(db_session, uid)
        first = memory_longterm.consolidate(db_session, uid, days=0)
        second = memory_longterm.consolidate(db_session, uid, days=0)
        assert first["episodes"] == 1
        assert second["skipped"] is True

    def test_fold_creates_memory_rows(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        # Fold facts directly (as the AI path would after normalization).
        concept = _make_concept(db_session, uid, "gradient descent")
        folded = memory_longterm._fold_facts(db_session, uid, [{"concept": "gradient descent", "strength_delta": 0.1}])
        assert folded == 1
        row = db_session.query(UserMemory).filter(
            UserMemory.user_id == uid, UserMemory.concept_id == concept.id
        ).first()
        assert row is not None
        assert row.strength > 0


class TestPromptInjection:
    def test_durable_facts_block(self, client, db_session):
        token = _signup(client)
        uid = _user_id(token)
        concept = _make_concept(db_session, uid, "entropy")
        db_session.add(UserMemory(user_id=uid, concept_id=concept.id, strength=0.7, exposure_count=2))
        db_session.commit()
        block = memory_longterm.durable_facts_block(db_session, uid)
        assert "entropy" in block
        assert "0.70" in block

    def test_empty_block_when_no_facts(self, client, db_session):
        token = _signup(client)
        assert memory_longterm.durable_facts_block(db_session, _user_id(token)) == ""


class TestIsolation:
    def test_episodes_are_per_user(self, client, db_session):
        token_a = _signup(client, "mem-a", "mema@test.com")
        uid_a = _user_id(token_a)
        token_b = _signup(client, "mem-b", "memb@test.com")
        uid_b = _user_id(token_b)
        topic = _make_topic(db_session, uid_a)
        db_session.add(LearningEvent(user_id=uid_a, topic_id=topic.id, event_type="quiz", value=0.7))
        db_session.commit()
        memory_longterm.append_episodes(db_session, uid_a)
        memory_longterm.append_episodes(db_session, uid_b)
        a_eps = db_session.query(EpisodicMemory).filter(EpisodicMemory.user_id == uid_a).count()
        b_eps = db_session.query(EpisodicMemory).filter(EpisodicMemory.user_id == uid_b).count()
        assert a_eps == 1
        assert b_eps == 0
