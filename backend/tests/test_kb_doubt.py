"""Idea 62 — AI doubt solving tests.

Covers the doubt endpoint: blocking-concept detection (prerequisite topics from
the DAG + kb_concepts matched against retrieved chunks), gap-first response
shape, learning-event logging, deterministic fallback with AI disabled, and
per-user isolation.
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


def _signup(client, db_session=None, uname="dbt-user", email="dbt@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Dbt", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    # Signup only flushes; the FTS drift-heal runs engine-level statements on
    # the shared in-memory connection and a later router ``db.rollback()`` can
    # wipe uncommitted rows — commit so the user survives the doubt requests.
    if db_session is not None:
        db_session.commit()
    return token


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


def _scan_md(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"doc{i}.md").write_text(text)
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "root_path": str(root)},
        headers=_auth(token),
    )
    src = resp.json()
    client.post(f"/api/kb/sources/{src['id']}/scan", headers=_auth(token))
    return src


def _by_name(topics, name):
    return next(t for t in topics if t["name"].lower() == name.lower())


class TestBlockingConcepts:
    def test_prerequisite_identified(self, client, db_session, tmp_path):
        token = _signup(client, db_session)
        profile, topics = _confirmed(client, token)
        prereq = _by_name(topics, "Linear algebra review")
        postreq = _by_name(topics, "Linear regression")

        # Build a DAG edge: prereq → postreq (Idea 62, phrase 12).
        from app.models import TopicDependency
        from app.services.security import decode_bearer_token

        user_id = decode_bearer_token(token)["user_id"]
        db_session.add(TopicDependency(
            user_id=user_id, subject_id=profile["curriculum_subject_id"],
            prereq_topic_id=prereq["id"], postreq_topic_id=postreq["id"],
            weight=1.0, provenance="test",
        ))
        db_session.commit()

        # A vault note covering the postreq topic so retrieval matches it.
        _scan_md(client, token, tmp_path,
                 ["Linear regression predicts a continuous target from features."])

        r = client.post(
            "/api/kb/tutor/doubt",
            json={"question": "linear regression predicts a continuous target",
                  "step_where_stuck": "stuck on choosing the loss function"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["blocking_concepts"], "expected a blocking concept"
        assert data["blocking_concepts"][0]["kind"] == "prerequisite"
        assert "Linear algebra review" in data["blocking_concepts"][0]["concept"]
        # Gap-first follow-ups offered.
        assert "review_prerequisite" in data["follow_ups"]

    def test_kb_concept_blocking(self, client, db_session, tmp_path):
        token = _signup(client, db_session)
        _confirmed(client, token)
        from app.models import KbConcept
        from app.services.security import decode_bearer_token

        user_id = decode_bearer_token(token)["user_id"]
        db_session.add(KbConcept(
            user_id=user_id, canonical_name="Maximum Likelihood",
            aliases='["MLE"]', definition="Estimating parameters that maximize data likelihood.",
        ))
        db_session.commit()
        _scan_md(client, token, tmp_path, ["MLE estimates model parameters."])

        r = client.post(
            "/api/kb/tutor/doubt",
            json={"question": "MLE estimates model parameters"},
            headers=_auth(token),
        )
        data = r.json()
        assert any(b["kind"] == "concept" for b in data["blocking_concepts"])

    def test_empty_retrieval_capture(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/tutor/doubt",
            json={"question": "stuck on tensor calculus"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["blocking_concepts"] == []
        assert data["follow_ups"] == ["capture"]
        assert "Second Brain" in data["answer"]


class TestEventsAndFallback:
    def test_doubt_logs_learning_event(self, client, db_session, tmp_path):
        token = _signup(client, db_session)
        profile, topics = _confirmed(client, token)
        _scan_md(client, token, tmp_path, ["Linear regression predicts targets."])
        client.post(
            "/api/kb/tutor/doubt",
            json={"question": "linear regression predicts targets"},
            headers=_auth(token),
        )
        from app.models import LearningEvent
        from app.services.security import decode_bearer_token

        user_id = decode_bearer_token(token)["user_id"]
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.event_type == "doubt")
            .all()
        )
        assert len(events) >= 1

    def test_deterministic_fallback_shape(self, client, tmp_path):
        # AI disabled (autouse) → the deterministic walkthrough lists the
        # blocking concepts + related notes, no LLM call.
        token = _signup(client)
        _confirmed(client, token)
        _scan_md(client, token, tmp_path, ["Linear regression predicts targets."])
        r = client.post(
            "/api/kb/tutor/doubt",
            json={"question": "linear regression predicts targets"},
            headers=_auth(token),
        )
        data = r.json()
        assert data["ai_used"] is False
        assert "Deterministic answer" in data["answer"]
        assert "try_practice_question" in data["follow_ups"]

    def test_uses_session_history(self, client, tmp_path):
        token = _signup(client)
        _scan_md(client, token, tmp_path, ["Linear regression predicts targets."])
        r = client.post(
            "/api/kb/tutor/chat",
            json={"message": "What is regression?"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["session_id"] > 0


class TestIsolation:
    def test_doubt_events_are_per_user(self, client, db_session, tmp_path):
        from app.services.security import decode_bearer_token

        t_a = _signup(client, db_session, "dbt-a", "dbta@test.com")
        t_b = _signup(client, db_session, "dbt-b", "dbtb@test.com")
        _confirmed(client, t_a)
        _scan_md(client, t_a, tmp_path, ["Linear regression predicts targets."])
        client.post(
            "/api/kb/tutor/doubt",
            json={"question": "linear regression predicts targets"},
            headers=_auth(t_a),
        )
        user_b = decode_bearer_token(t_b)["user_id"]
        from app.models import LearningEvent

        events_b = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.user_id == user_b, LearningEvent.event_type == "doubt")
            .all()
        )
        assert events_b == []
