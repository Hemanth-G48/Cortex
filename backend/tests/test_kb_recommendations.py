"""Idea 97 — recommendation engine tests.

Cross-domain candidate generation, ranking math (urgency × weakness ×
readiness), explainable reasons, feedback logging into ai_logs, and per-user
isolation.
"""
from __future__ import annotations

import pytest

from app.models import AiLog
from app.services.kb import recommendations as rec_service
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Machine Learning

## Unit 1: Foundations
- Linear regression
- Gradient descent

## Unit 2: Advanced
- Neural networks
- Regularization
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="rec-user", email="rec@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Rec", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


class TestCandidates:
    def test_study_domain_present(self, client):
        token = _signup(client)
        _confirmed(client, token)
        r = client.get("/api/kb/recommendations", headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["weights"]["urgency"] + body["weights"]["weakness"] + body["weights"]["readiness"] == pytest.approx(1.0)
        assert body["items"]
        assert all(i["reason"] for i in body["items"])
        assert all(i["score"] > 0 for i in body["items"])

    def test_reasons_are_explainable(self, client):
        token = _signup(client)
        _confirmed(client, token)
        r = client.get("/api/kb/recommendations", headers=_auth(token))
        for item in r.json()["items"]:
            assert item["reason"].startswith("because")
            assert item["id"].startswith(item["domain"] + ":")

    def test_ranking_uses_weights(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _confirmed(client, token)
        items = rec_service.candidates(db_session, uid, limit=10)
        # Recompute expected score from the same weights.
        weights = rec_service.settings.kb_recommendation_weights
        for item in items:
            expected = round(
                weights["urgency"] * item["urgency"]
                + weights["weakness"] * item["weakness"]
                + weights["readiness"] * item["readiness"],
                4,
            )
            assert item["score"] == expected

    def test_feedback_logged(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _confirmed(client, token)
        r = client.get("/api/kb/recommendations", headers=_auth(token))
        first = r.json()["items"][0]
        fb = client.post(
            f"/api/kb/recommendations/{first['id']}/feedback",
            json={"action": "accept"},
            headers=_auth(token),
        )
        assert fb.status_code == 200, fb.text
        rows = db_session.query(AiLog).filter(
            AiLog.user_id == uid, AiLog.feature == "recommend"
        ).all()
        assert len(rows) == 1
        assert rows[0].feedback == 1
        assert rows[0].request == first["id"]


class TestIsolation:
    def test_recommendations_are_per_user(self, client, db_session):
        token_a = _signup(client, "rec-a", "reca@test.com")
        token_b = _signup(client, "rec-b", "recb@test.com")
        _confirmed(client, token_a)
        # User B has no topics → empty feed.
        r = client.get("/api/kb/recommendations", headers=_auth(token_b))
        assert r.json()["items"] == []
        # B cannot log feedback for A's item id (still allowed — item ids are
        # opaque keys — but the row lands under B's user).
        client.post(
            "/api/kb/recommendations/study:1/feedback",
            json={"action": "skip"},
            headers=_auth(token_b),
        )
        rows = db_session.query(AiLog).filter(AiLog.user_id == _uid(token_b)).all()
        assert len(rows) == 1
