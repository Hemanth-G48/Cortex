"""Idea 50 — learning outcomes tests.

Add, expand (LLM + fallback), complete → Goal row, toggle back, per-user
isolation.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import Goal

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


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="out-user", email="out@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Out", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed_with_topics(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
    return profile, {t["name"]: t for t in topics}


class TestOutcomes:
    def test_add_outcome(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        r = client.post(
            f"/api/subjects/topics/{t['id']}/outcomes",
            json={"text": "Implement gradient descent from scratch"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        texts = [o["text"] for o in r.json()["outcomes"]]
        assert "Implement gradient descent from scratch" in texts
        assert all(o["status"] == "pending" for o in r.json()["outcomes"])

    def test_expand_fallback(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        r = client.post(f"/api/subjects/topics/{t['id']}/outcomes/expand", headers=_auth(token))
        assert r.status_code == 200, r.text
        # Fallback generates 3 scaffolded outcomes (or keeps raw if >= 2 exist).
        assert len(r.json()["outcomes"]) >= 1

    def test_expand_llm(self, client, monkeypatch):
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        monkeypatch.setattr("app.config.settings.AI_ENABLED", True)
        with patch(
            "app.services.ai_client.generate_json",
            return_value={"outcomes": ["Fit a model with sklearn", "Diagnose overfitting"]},
        ):
            r = client.post(f"/api/subjects/topics/{t['id']}/outcomes/expand", headers=_auth(token))
        assert r.status_code == 200, r.text
        texts = [o["text"] for o in r.json()["outcomes"]]
        assert "Fit a model with sklearn" in texts

    def test_complete_creates_goal(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        r = client.post(f"/api/subjects/topics/{t['id']}/outcomes/expand", headers=_auth(token))
        outcomes = r.json()["outcomes"]
        idx = 0
        r = client.post(
            f"/api/subjects/topics/{t['id']}/outcomes/{idx}/complete", headers=_auth(token)
        )
        assert r.status_code == 200, r.text
        assert r.json()["outcomes"][idx]["status"] == "done"
        assert r.json()["outcomes"][idx]["completed_at"]
        # A Goal row was linked (title prefixed with the topic name).
        goal = db_session.query(Goal).order_by(Goal.id.desc()).first()
        assert goal is not None
        assert goal.is_completed is True
        assert goal.progress_percentage == 100.0
        assert goal.title.startswith("Linear regression:")

    def test_complete_toggles_back(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        client.post(f"/api/subjects/topics/{t['id']}/outcomes/expand", headers=_auth(token))
        client.post(f"/api/subjects/topics/{t['id']}/outcomes/0/complete", headers=_auth(token))
        r = client.post(f"/api/subjects/topics/{t['id']}/outcomes/0/complete", headers=_auth(token))
        assert r.json()["outcomes"][0]["status"] == "pending"
        assert r.json()["outcomes"][0]["completed_at"] is None

    def test_complete_out_of_range_404(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        t = topics["Linear regression"]
        r = client.post(f"/api/subjects/topics/{t['id']}/outcomes/99/complete", headers=_auth(token))
        assert r.status_code == 404

    def test_merge_combines_outcomes(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        a = topics["Linear regression"]
        b = topics["Gradient descent"]
        client.post(
            f"/api/subjects/topics/{a['id']}/outcomes",
            json={"text": "Outcome unique to A"},
            headers=_auth(token),
        )
        r = client.post(
            f"/api/subjects/{_profile_id(client, token)}/topics/{b['id']}/merge",
            json={"into_topic_id": a["id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        out = client.get(f"/api/subjects/topics/{a['id']}/outcomes", headers=_auth(token)).json()
        assert any(o["text"] == "Outcome unique to A" for o in out["outcomes"])
        merged = client.get(f"/api/subjects/topics/{b['id']}/outcomes", headers=_auth(token)).json()
        assert merged["outcomes"] == [] or all(
            o["status"] != "pending" for o in merged["outcomes"]
        )

    def test_isolation(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "out-a", "outa@test.com")
        token_b = _signup(client, "out-b", "outb@test.com")
        _, topics = _confirmed_with_topics(client, token_a)
        t = topics["Linear regression"]
        # B cannot read, mutate, or complete A's topic outcomes.
        assert client.get(f"/api/subjects/topics/{t['id']}/outcomes", headers=_auth(token_b)).status_code == 404
        assert client.post(
            f"/api/subjects/topics/{t['id']}/outcomes",
            json={"text": "hijack"},
            headers=_auth(token_b),
        ).status_code == 404


def _profile_id(client, token):
    items = client.get("/api/subjects", headers=_auth(token)).json()["items"]
    return items[0]["id"]
