"""Idea 67 — adaptive question difficulty tests.

Covers mastery-gated tier selection, the IRT-lite accuracy-threshold update
rule (raise/lower next tier), per-(user, topic) state persistence, clamping to
available tiers, and learning-event emission.
"""
from __future__ import annotations

import pytest

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


def _signup(client, uname="adp-user", email="adp@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Adp", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _first_topic(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topic = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"][0]
    return profile, topic


def _seed_bank(db_session, token, topic_id, difficulties=("E", "M", "H")):
    """Insert + approve one distinct question per difficulty tier (avoids the
    deterministic fallback's identical-text dedupe)."""
    from app.models import PracticeQuestion
    from app.services.kb import KbService
    from app.services.kb.questions import question_hash
    from app.services.security import decode_bearer_token

    user_id = decode_bearer_token(token)["user_id"]
    for i, d in enumerate(difficulties):
        text = f"Unique tier-{d} question about the topic ({i})"
        db_session.add(PracticeQuestion(
            user_id=user_id,
            topic_id=topic_id,
            question=text,
            options=KbService.json_dumps([f"Option A {i}", f"Option B {i}", f"Option C {i}", f"Option D {i}"]),
            answer=f"Option A {i}",
            explanation="Explanation",
            bloom_level="Understand",
            difficulty=d,
            status="approved",
            question_hash=question_hash(text),
        ))
    db_session.commit()


class TestSelectTier:
    def test_unknown_mastery_starts_medium(self, client, db_session):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        r = client.post(
            "/api/kb/practice/session",
            json={"topic_id": topic["id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session"]["tier"] == "M"
        assert data["session"]["available_tiers"] == ["E", "M", "H"]
        assert "started from mastery classification" in data["session"]["reason"]

    def test_strong_mastery_starts_hard(self, client, db_session):
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        user_id = decode_bearer_token(token)["user_id"]
        for _ in range(6):
            log_event(db_session, user_id, event_type="quiz",
                      topic_id=topic["id"], value=1.0)
        db_session.commit()

        data = client.post(
            "/api/kb/practice/session",
            json={"topic_id": topic["id"]},
            headers=_auth(token),
        ).json()
        assert data["session"]["tier"] == "H"

    def test_clamps_to_available_tiers(self, client, db_session):
        # Only E-tier questions exist → selection clamps down to E.
        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"], difficulties=("E",))
        data = client.post(
            "/api/kb/practice/session",
            json={"topic_id": topic["id"]},
            headers=_auth(token),
        ).json()
        assert data["session"]["tier"] == "E"

    def test_unknown_topic_404(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/practice/session",
            json={"topic_id": 9999},
            headers=_auth(token),
        )
        assert r.status_code == 404


class TestRecordAnswer:
    def test_correct_answers_raise_tier(self, client, db_session):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        topic_id = topic["id"]

        # Start at M. Three perfect answers push accuracy ≥ 0.7 → raise to H.
        tier = "M"
        for _ in range(3):
            r = client.post(
                "/api/kb/practice/answer",
                json={"topic_id": topic_id, "tier": tier, "correct": True},
                headers=_auth(token),
            )
            assert r.status_code == 200, r.text
            data = r.json()
            tier = data["tier"]
        assert tier == "H"
        assert data["streak"] == 3

    def test_wrong_answers_reset_streak(self, client, db_session):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        topic_id = topic["id"]

        client.post(
            "/api/kb/practice/answer",
            json={"topic_id": topic_id, "tier": "M", "correct": True},
            headers=_auth(token),
        )
        r = client.post(
            "/api/kb/practice/answer",
            json={"topic_id": topic_id, "tier": "M", "correct": False},
            headers=_auth(token),
        )
        data = r.json()
        assert data["streak"] == 0

    def test_state_persists_per_user_topic(self, client, db_session):
        from app.models import AdaptiveState
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        user_id = decode_bearer_token(token)["user_id"]
        client.post(
            "/api/kb/practice/answer",
            json={"topic_id": topic["id"], "tier": "M", "correct": True},
            headers=_auth(token),
        )
        row = (
            db_session.query(AdaptiveState)
            .filter(AdaptiveState.user_id == user_id, AdaptiveState.topic_id == topic["id"])
            .first()
        )
        assert row is not None
        assert row.streak == 1

    def test_practice_event_logged(self, client, db_session):
        from app.models import LearningEvent
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topic = _first_topic(client, token)
        _seed_bank(db_session, token, topic["id"])
        user_id = decode_bearer_token(token)["user_id"]
        client.post(
            "/api/kb/practice/answer",
            json={"topic_id": topic["id"], "tier": "M", "correct": True},
            headers=_auth(token),
        )
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.event_type == "practice")
            .all()
        )
        assert len(events) == 1

    def test_isolation(self, client, db_session):
        t_a = _signup(client, "adp-a", "adpa@test.com")
        t_b = _signup(client, "adp-b", "adpb@test.com")
        _, topic = _first_topic(client, t_a)
        _seed_bank(db_session, t_a, topic["id"])
        # B cannot record answers on A's topic.
        r = client.post(
            "/api/kb/practice/answer",
            json={"topic_id": topic["id"], "tier": "M", "correct": True},
            headers=_auth(t_b),
        )
        assert r.status_code == 404
