"""Idea 45 — unit & lecture segmentation tests.

Name matching, embedding fallback (mocked), confirm writes topic links,
unmatched \"create new\" flow.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import CurriculumUnit, Topic
from app.services.kb.units import name_similarity
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Algorithms

Fall 2026

## Unit 1: Sorting
- Bubble sort
- Merge sort

## Unit 2: Graphs
- BFS
- Dijkstra
"""


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="unit-user", email="unit@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Unit", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    r = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    return r.json()["profile"]


class TestNameMatch:
    def test_similarity_scores(self):
        assert name_similarity("Sorting", "Sorting") == 1.0
        assert name_similarity("Sorting Algorithms", "Sorting") >= 0.5
        # Dissimilar pair scores well below the 0.55 match threshold.
        assert name_similarity("Graphs and Trees", "Databases") < 0.55

    def test_match_candidates(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        # Existing curriculum units created by confirm already match by name.
        r = client.get(f"/api/subjects/{profile['id']}/match-units", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == 2
        sorting = next(i for i in items if i["title"] == "Sorting")
        assert sorting["match_type"] == "name"
        assert sorting["score"] >= 0.55
        assert sorting["candidate_unit_id"] is not None

    def test_embedding_fallback(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        # Sabotage name matching by renaming the existing unit.
        with patch("app.services.kb.units.name_similarity", return_value=0.0):
            with patch(
                "app.services.kb.units._embedding_match",
                return_value=0.9,
            ):
                r = client.get(
                    f"/api/subjects/{profile['id']}/match-units?use_embeddings=true",
                    headers=_auth(token),
                )
        items = r.json()["items"]
        matched = [i for i in items if i["match_type"] == "embedding"]
        assert matched and matched[0]["score"] == 0.9

    def test_embedding_skipped_when_unavailable(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        # The app's deterministic hash-embedding fallback always yields vectors
        # (identical titles => cosine 1.0), so simulate genuinely-unavailable
        # embeddings to verify the "none" fallback path.
        with patch("app.services.kb.units.name_similarity", return_value=0.0), patch(
            "app.services.kb.units._embedding_match", return_value=0.0
        ):
            r = client.get(
                f"/api/subjects/{profile['id']}/match-units?use_embeddings=true",
                headers=_auth(token),
            )
        assert all(i["match_type"] == "none" for i in r.json()["items"])


class TestConfirm:
    def test_confirm_assigns_topic_units(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        r = client.get(f"/api/subjects/{profile['id']}/match-units", headers=_auth(token))
        items = r.json()["items"]
        mapping = {i["title"]: i["candidate_unit_id"] for i in items}
        r = client.post(
            f"/api/subjects/{profile['id']}/match-units/confirm",
            json={"mapping": mapping},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["topics_assigned"] == 4
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        assert all(t["unit_id"] is not None for t in topics)

    def test_unmatched_flow(self, client, monkeypatch):
        """Phrase 47: parsed units with no candidate come back as create-new."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        with patch("app.services.kb.units.name_similarity", return_value=0.0):
            r = client.get(f"/api/subjects/{profile['id']}/match-units", headers=_auth(token))
        items = r.json()["items"]
        assert all(i["candidate_unit_id"] is None for i in items)
        assert all(i["match_type"] == "none" for i in items)


class TestIsolation:
    def test_per_user_404(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "unit-a", "unita@test.com")
        token_b = _signup(client, "unit-b", "unitb@test.com")
        profile = _confirmed(client, token_a)
        r = client.get(f"/api/subjects/{profile['id']}/match-units", headers=_auth(token_b))
        assert r.status_code == 404
