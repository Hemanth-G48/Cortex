"""Idea 59 — "what should I study now" tests.

Recommendation scoring favors weak + due + exam-proximate topics; unready
(blocked) topics are never recommended when a ready one exists; the blocking
prerequisite is surfaced; per-user + per-subject scoping.
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

## Unit 3: Classification
- Logistic regression
- Decision trees
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="next-user", email="next@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Next", "username": uname, "email": email,
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


class TestRecommend:
    def test_empty_when_no_topics(self, client):
        token = _signup(client)
        assert client.get("/api/subjects-ai/next-action", headers=_auth(token)).json()["items"] == []

    def test_recommends_topics_with_reasons(self, client):
        token = _signup(client)
        _, topics = _confirmed(client, token)
        r = client.get("/api/subjects-ai/next-action", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert 1 <= len(items) <= 3
        item = items[0]
        assert item["topic_id"] in {t["id"] for t in topics}
        assert item["ready"] is True
        # Phase 8 extended the factor set with concept gaps + subject coverage
        # (settings.kb_recommend_weights) — both present from day one.
        assert set(item["reasons"]) == {
            "readiness", "weakness", "due_reviews", "concept_gaps",
            "exam_proximity", "subject_coverage",
        }
        assert item["blocked_by"] == []

    def test_weak_topic_ranks_first(self, client, db_session):
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topics = _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        # Boost topic 0 to strong; topic 1 stays at 0 (weakest).
        for _ in range(6):
            log_event(db_session, user_id, event_type="quiz", topic_id=topics[0]["id"], value=1.0)
        db_session.commit()
        items = client.get("/api/subjects-ai/next-action", headers=_auth(token)).json()["items"]
        assert items[0]["topic_id"] == topics[1]["id"]  # weakest first

    def test_blocked_topic_not_recommended(self, client, db_session):
        from app.models import TopicDependency
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _, topics = _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        # topic 2 depends on topic 0; neither has mastery → topic 2 blocked.
        db_session.add(
            TopicDependency(
                user_id=user_id,
                subject_id=topics[0]["subject_id"],
                prereq_topic_id=topics[0]["id"],
                postreq_topic_id=topics[1]["id"],
            )
        )
        db_session.commit()
        items = client.get("/api/subjects-ai/next-action", headers=_auth(token)).json()["items"]
        assert all(i["topic_id"] != topics[1]["id"] for i in items)

    def test_subject_scoped(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        r = client.get(
            f"/api/subjects-ai/next-action?subject_id={profile['curriculum_subject_id']}",
            headers=_auth(token),
        )
        assert r.status_code == 200
        items = r.json()["items"]
        assert all(i["subject_id"] == profile["curriculum_subject_id"] for i in items)
        # Different subject id → empty.
        r2 = client.get("/api/subjects-ai/next-action?subject_id=99999", headers=_auth(token))
        assert r2.json()["items"] == []


class TestIsolation:
    def test_next_action_is_per_user(self, client):
        token_a = _signup(client, "next-a", "nexta@test.com")
        token_b = _signup(client, "next-b", "nextb@test.com")
        _, topics = _confirmed(client, token_a)
        assert client.get("/api/subjects-ai/next-action", headers=_auth(token_b)).json()["items"] == []
        assert client.get("/api/subjects-ai/next-action", headers=_auth(token_a)).json()["items"]
