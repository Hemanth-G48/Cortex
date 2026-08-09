"""Idea 48 — topic difficulty estimation tests.

Fallback heuristic, LLM rubric (mocked), concept-overlap bias, density bias,
manual override authority, per-user isolation.
"""
from __future__ import annotations

from unittest.mock import patch

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


def _signup(client, uname="diff-user", email="diff@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Diff", "username": uname, "email": email,
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


class TestEstimateDifficulty:
    def test_fallback_keywords(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        from app.services.kb.topics import estimate_difficulty

        _signup(client)

        # Pure keyword routing with a null-safe db stub (no real DB needed).
        class _StubDB:
            def query(self, _):
                return self

            def filter(self, _):
                return self

            def all(self):
                return []

        db = _StubDB()
        hard, conf_h = estimate_difficulty(db, 1, "Complexity analysis of algorithms", None, [])
        assert hard == "H"
        easy, conf_e = estimate_difficulty(db, 1, "Introduction to history basics", None, [])
        assert easy == "E"
        mid, _ = estimate_difficulty(db, 1, "Regression models", None, ["Apply linear regression"])
        assert mid == "M"
        assert 0.0 <= conf_h <= 1.0 and 0.0 <= conf_e <= 1.0

    def test_llm_rubric_wins(self, client, monkeypatch):
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        # Force recompute through the API with a mocked rubric.
        monkeypatch.setattr("app.config.settings.AI_ENABLED", True)
        with patch(
            "app.services.ai_client.generate_json",
            return_value={"difficulty": "H", "confidence": 0.9},
        ):
            r = client.post(
                f"/api/subjects/topics/{topics['Linear regression']['id']}/recompute",
                headers=_auth(token),
            )
        assert r.status_code == 200, r.text
        assert r.json()["topic"]["difficulty"] == "H"
        assert r.json()["topic"]["difficulty_confidence"] == 0.9

    def test_llm_bad_rubric_falls_back(self, client, monkeypatch):
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        monkeypatch.setattr("app.config.settings.AI_ENABLED", True)
        with patch("app.services.ai_client.generate_json", return_value={"difficulty": "X"}):
            r = client.post(
                f"/api/subjects/topics/{topics['Linear regression']['id']}/recompute",
                headers=_auth(token),
            )
        assert r.status_code == 200, r.text
        assert r.json()["topic"]["difficulty"] in ("E", "M", "H")

    def test_concept_overlap_bias(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        from app.models import KbConcept
        from app.services.kb.topics import estimate_difficulty
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        db_session.add(KbConcept(user_id=user_id, canonical_name="regression models"))
        db_session.commit()
        # "Regression models" is medium; known concept bumps toward Hard.
        hard, conf = estimate_difficulty(db_session, user_id, "Regression models", None, [])
        assert hard == "H"
        assert conf > 0

    def test_density_bias(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        from app.services.kb.topics import estimate_difficulty
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        # Medium keyword topic + a huge content volume (chars > 4000).
        d, _ = estimate_difficulty(
            db_session, user_id, "Regression models", None, [], chars=9000
        )
        assert d == "H"


class TestManualOverride:
    def test_manual_override_authoritative(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        r = client.patch(
            f"/api/subjects/topics/{topics['Linear regression']['id']}",
            json={"difficulty": "E", "first_pass_mins": 30},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        t = r.json()["topic"]
        assert t["difficulty"] == "E"
        assert t["difficulty_confidence"] == 1.0
        assert t["first_pass_mins"] == 30

    def test_recompute_clears_manual_confidence(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        _, topics = _confirmed_with_topics(client, token)
        client.patch(
            f"/api/subjects/topics/{topics['Linear regression']['id']}",
            json={"difficulty": "E"},
            headers=_auth(token),
        )
        r = client.post(
            f"/api/subjects/topics/{topics['Linear regression']['id']}/recompute",
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["topic"]["difficulty_confidence"] < 1.0

    def test_patch_other_user_topic_404(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "diff-a", "diffa@test.com")
        token_b = _signup(client, "diff-b", "diffb@test.com")
        _, topics = _confirmed_with_topics(client, token_a)
        r = client.patch(
            f"/api/subjects/topics/{topics['Linear regression']['id']}",
            json={"difficulty": "H"},
            headers=_auth(token_b),
        )
        assert r.status_code == 404
