"""Idea 49 — time estimation tests.

Formula (volume × difficulty factor), pacing multiplier scaling, per-topic
time-budget endpoint, per-user isolation.
"""
from __future__ import annotations

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


def _signup(client, uname="time-user", email="time@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Time", "username": uname, "email": email,
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


class TestFormula:
    def test_pure_formula(self):
        from app.services.kb.topics import estimate_times

        # 1800 chars ≈ 10 min first-pass at base rate (E factor 1.0) → min 15.
        first, review, mastery = estimate_times(1800, "E")
        assert first >= 15
        assert review == max(5, round(first * 0.4))
        assert mastery == max(5, round(first * 0.6))

    def test_harder_topic_takes_longer(self):
        from app.services.kb.topics import estimate_times

        e = estimate_times(5000, "E")
        m = estimate_times(5000, "M")
        h = estimate_times(5000, "H")
        assert e[0] < m[0] < h[0]

    def test_pacing_multiplier_scales(self):
        from app.services.kb.topics import estimate_times

        base = estimate_times(5000, "M", multiplier=1.0)
        slow = estimate_times(5000, "M", multiplier=2.0)
        assert slow[0] == round(base[0] * 2)
        assert slow[1] == round(base[1] * 2)
        assert slow[2] == round(base[2] * 2)

    def test_multiplier_floor(self):
        from app.services.kb.topics import estimate_times

        # Multiplier clamps to >= 0.1, never zero/negative.
        first, review, mastery = estimate_times(5000, "M", multiplier=0.0)
        assert first >= 5 and review >= 5 and mastery >= 5


class TestEndpoints:
    def test_topics_have_estimates(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        items = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        assert items
        for t in items:
            assert t["first_pass_mins"] >= 5
            assert t["review_mins"] >= 5
            assert t["mastery_mins"] >= 5
            assert t["difficulty"] in ("E", "M", "H")

    def test_time_budget_totals(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.get(f"/api/subjects/{profile['id']}/time-budget", headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["pacing_multiplier"] == 1.0
        assert len(data["items"]) >= 4
        assert data["total_first_pass_mins"] == sum(
            t["first_pass_mins"] for t in data["items"]
        )

    def test_pacing_setting_persists(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.put("/api/subjects/me/pacing", json={"multiplier": 1.5}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["pacing_multiplier"] == 1.5
        data = client.get(f"/api/subjects/{profile['id']}/time-budget", headers=_auth(token)).json()
        assert data["pacing_multiplier"] == 1.5

    def test_pacing_invalid(self, client):
        token = _signup(client)
        r = client.put("/api/subjects/me/pacing", json={"multiplier": 0.0}, headers=_auth(token))
        assert r.status_code == 422

    def test_time_budget_per_user(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "time-a", "timea@test.com")
        token_b = _signup(client, "time-b", "timeb@test.com")
        profile = _confirmed(client, token_a)
        assert client.get(
            f"/api/subjects/{profile['id']}/time-budget", headers=_auth(token_b)
        ).status_code == 404
