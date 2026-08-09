"""Idea 47 — learning roadmap tests.

Generation (weekly budget bucketing), deadline-aware spread, versioning
(previous actives archived), per-user isolation.
"""
from __future__ import annotations

from app.models import Roadmap
from app.services.security import decode_bearer_token

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


def _signup(client, uname="roadmap-user", email="roadmap@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Roadmap", "username": uname, "email": email,
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
    def test_generates_active_roadmap(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate",
            json={},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        roadmap = r.json()["roadmap"]
        assert roadmap["status"] == "active"
        assert roadmap["version"] == 1
        assert roadmap["plan"]["weekly_budget_minutes"] == 300
        assert roadmap["plan"]["weeks"]
        # Every topic appears in exactly one week.
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        seen = [t for w in roadmap["plan"]["weeks"] for t in w["topic_ids"]]
        assert len(seen) == len({s for s in seen}) == len(topics)

    def test_weekly_budget_respected(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        # Tiny budget forces one topic per week (topics have est >= 15m).
        r = client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate",
            json={"weekly_budget": 60},
            headers=_auth(token),
        )
        weeks = r.json()["roadmap"]["plan"]["weeks"]
        assert all(w["est_mins"] <= 60 for w in weeks)

    def test_deadline_spreads_evenly(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        import datetime

        deadline = (datetime.date.today() + datetime.timedelta(days=28)).isoformat()
        r = client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate",
            json={"deadline": deadline},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        weeks = r.json()["roadmap"]["plan"]["weeks"]
        # 28 days from today => up to 4 weeks; 6 topics across <= 4 weeks.
        assert len(weeks) <= 4

    def test_budget_min_clamped(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate",
            json={"weekly_budget": 10},
            headers=_auth(token),
        )
        assert r.status_code == 422  # below the API's ge=60 floor


class TestVersioning:
    def test_new_generation_archives_previous(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        for _ in range(2):
            r = client.post(
                f"/api/subjects/{profile['id']}/roadmap/generate",
                json={},
                headers=_auth(token),
            )
            assert r.status_code == 200
        # Latest active is version 2; version 1 archived.
        active = client.get(f"/api/subjects/{profile['id']}/roadmap", headers=_auth(token)).json()["roadmap"]
        assert active["version"] == 2
        assert active["status"] == "active"
        rows = (
            db_session.query(Roadmap)
            .filter(Roadmap.user_id == decode_bearer_token(token)["user_id"])
            .order_by(Roadmap.version.asc())
            .all()
        )
        assert [r.version for r in rows] == [1, 2]
        assert rows[0].status == "archived"

    def test_no_roadmap_yet(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.get(f"/api/subjects/{profile['id']}/roadmap", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["roadmap"] is None

    def test_roadmap_before_confirm_400(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
        profile = r.json()["profile"]
        r = client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate", json={}, headers=_auth(token)
        )
        assert r.status_code == 400


class TestIsolation:
    def test_roadmap_is_per_user(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "road-a", "roada@test.com")
        token_b = _signup(client, "road-b", "roadb@test.com")
        profile = _confirmed(client, token_a)
        client.post(f"/api/subjects/{profile['id']}/roadmap/generate", json={}, headers=_auth(token_a))
        # User B can't read or generate for A's profile.
        assert client.get(f"/api/subjects/{profile['id']}/roadmap", headers=_auth(token_b)).status_code == 404
        assert client.post(
            f"/api/subjects/{profile['id']}/roadmap/generate", json={}, headers=_auth(token_b)
        ).status_code == 404
