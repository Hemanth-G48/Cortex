"""Idea 51 — personalized study plan tests.

Topic-grounded plan generation (fallback deterministic: topological order →
equal weekly split), weekly coverage of every topic, availability constraints,
per-user isolation, unconfirmed-profile 400.
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


def _signup(client, uname="plan-user", email="plan@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Plan", "username": uname, "email": email,
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


class TestGenerate:
    def test_generates_weekly_plan_covering_all_topics(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/study-plan",
            json={"hours_per_day": 2.0, "weeks": 3},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        assert plan["subject"]
        assert plan["weeks"]
        # Every confirmed topic appears in exactly one week.
        topics = client.get(
            f"/api/subjects/{profile['id']}/topics", headers=_auth(token)
        ).json()["items"]
        seen = [t for w in plan["weeks"] for t in w["topic_ids"]]
        assert len(seen) == len({s for s in seen}) == len(topics)
        # Week numbers are 1-based sequential.
        assert [w["week"] for w in plan["weeks"]] == list(range(1, len(plan["weeks"]) + 1))

    def test_week_budget_respected(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/study-plan",
            json={"weeks": 6},  # 6 topics, 6 weeks → ~1 topic/week
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        weeks = r.json()["plan"]["weeks"]
        assert len(weeks) == 6
        assert all(len(w["topic_ids"]) == 1 for w in weeks)

    def test_invalid_budget_422(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/study-plan",
            json={"hours_per_day": 99},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_unconfirmed_profile_400(self, client):
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
        profile = r.json()["profile"]
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/study-plan",
            json={},
            headers=_auth(token),
        )
        assert r.status_code == 400


class TestGet:
    def test_returns_latest_plan(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects-ai/{profile['id']}/study-plan", json={}, headers=_auth(token))
        r = client.get(f"/api/subjects-ai/{profile['id']}/study-plan", headers=_auth(token))
        assert r.status_code == 200, r.text
        plan = r.json()["plan"]
        assert plan is not None
        assert plan["weeks"]

    def test_none_when_no_plan(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.get(f"/api/subjects-ai/{profile['id']}/study-plan", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["plan"] is None


class TestIsolation:
    def test_plan_is_per_user(self, client):
        token_a = _signup(client, "plan-a", "plana@test.com")
        token_b = _signup(client, "plan-b", "planb@test.com")
        profile = _confirmed(client, token_a)
        client.post(f"/api/subjects-ai/{profile['id']}/study-plan", json={}, headers=_auth(token_a))
        # User B cannot read or generate for A's profile.
        assert client.get(
            f"/api/subjects-ai/{profile['id']}/study-plan", headers=_auth(token_b)
        ).status_code == 404
        assert client.post(
            f"/api/subjects-ai/{profile['id']}/study-plan", json={}, headers=_auth(token_b)
        ).status_code == 404
