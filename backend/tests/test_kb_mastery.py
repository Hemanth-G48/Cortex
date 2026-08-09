"""Idea 58 — mastery engine + weak-topics endpoint tests.

``log_event`` recomputes mastery on write; classification thresholds
(unknown below MIN_EVIDENCE, weak < 0.4, strong ≥ 0.75); quiz accuracy moves
the score; weak-topics endpoint ranks weak/unknown topics and excludes strong
ones; per-user isolation.
"""
from __future__ import annotations

import pytest

from app.services.kb.mastery import _mastery_from_events, classify

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


def _signup(client, uname="mas-user", email="mas@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mas", "username": uname, "email": email,
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
    profile = confirmed.json()["profile"]  # now carries curriculum_subject_id
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
    return profile, topics


class TestEngine:
    def test_no_events_zero(self):
        assert _mastery_from_events([]) == 0.0

    def test_classify_needs_min_evidence(self):
        assert classify(0.9, 1) == "unknown"  # 1 event isn't enough evidence

    def test_classify_thresholds(self):
        assert classify(0.2, 5) == "weak"
        assert classify(0.6, 5) == "medium"
        assert classify(0.85, 5) == "strong"

    def test_quiz_accuracy_raises_score(self, client, db_session):
        from app.models import Topic
        from app.services.kb.mastery import log_event, recompute_mastery
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topics = _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        log_event(db_session, user_id, event_type="quiz", topic_id=topics[0]["id"], value=0.9)
        log_event(db_session, user_id, event_type="quiz", topic_id=topics[0]["id"], value=1.0)
        db_session.commit()
        # Recompute now that both events are committed (autoflush is off).
        recompute_mastery(db_session, user_id, topics[0]["id"])
        db_session.commit()

        row = db_session.query(Topic).get(topics[0]["id"])
        assert row.mastery_score > 0.5
        assert row.mastery_classification in ("medium", "strong")


class TestWeakTopics:
    def test_all_unknown_when_no_evidence(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        r = client.get("/api/subjects-ai/weak-topics", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        # Every topic is unknown (no evidence) → all listed.
        assert {i["topic_id"] for i in items} == {t["id"] for t in topics}
        assert all(i["classification"] == "unknown" for i in items)

    def test_strong_topics_excluded(self, client, db_session):
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        profile, topics = _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        # Make topic 0 strong: 6 perfect quiz scores.
        for _ in range(6):
            log_event(db_session, user_id, event_type="quiz", topic_id=topics[0]["id"], value=1.0)
        db_session.commit()
        items = client.get("/api/subjects-ai/weak-topics", headers=_auth(token)).json()["items"]
        assert all(i["topic_id"] != topics[0]["id"] for i in items)

    def test_filter_by_subject(self, client, db_session):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        r = client.get(
            f"/api/subjects-ai/weak-topics?subject_id={profile['curriculum_subject_id']}",
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert len(r.json()["items"]) == len(topics)

    def test_weak_topics_is_per_user(self, client):
        token_a = _signup(client, "mas-a", "masa@test.com")
        token_b = _signup(client, "mas-b", "masb@test.com")
        _, topics = _confirmed(client, token_a)
        # B has no topics → empty list.
        assert client.get("/api/subjects-ai/weak-topics", headers=_auth(token_b)).json()["items"] == []
        assert client.get("/api/subjects-ai/weak-topics", headers=_auth(token_a)).json()["total"] == len(topics)
