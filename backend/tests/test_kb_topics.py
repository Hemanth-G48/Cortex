"""Idea 44 — topic extraction & normalization tests.

Extraction from a confirmed profile, synonym folding through kb_concepts,
Bloom fallback, review lifecycle (confirm/merge/reject), dedupe by normalized
name.
"""
from __future__ import annotations

from app.models import KbConcept, Topic
from app.services.security import decode_bearer_token

SYLLABUS = """\
# Databases

Fall 2026

## Unit 1: Relational Model
- Introduction to relations
- SQL queries
- Normalization
1. Design database schemas
2. Analyze query performance

## Unit 2: Transactions
- ACID properties
- Concurrency control
Upon completion, students will be able to explain transaction isolation.
"""


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="topic-user", email="topic@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Topic", "username": uname, "email": email,
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


class TestExtraction:
    def test_generate_creates_pending_topics(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["generated"] == 7  # 4 + 2 + 1 (last line is outcome-only topic? no)
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        names = {t["name"] for t in topics}
        assert "SQL queries" in names and "Normalization" in names
        assert all(t["status"] == "pending" for t in topics)
        # Estimates computed (difficulty + times).
        for t in topics:
            assert t["difficulty"] in ("E", "M", "H")
            assert t["first_pass_mins"] > 0

    def test_dedupe_by_normalized_name(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        first = client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        assert first.json()["generated"] > 0
        # Re-running must not create duplicates (normalized-name dedupe).
        second = client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        assert second.status_code == 200
        assert second.json()["generated"] == 0
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        normalized = [t["normalized_name"] for t in topics]
        assert len(normalized) == len(set(normalized))

    def test_synonym_folding_through_concepts(self, client, monkeypatch, db_session):
        """Phrase 34: a topic whose name is a concept alias folds to canonical."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        db_session.add(KbConcept(user_id=user_id, canonical_name="structured query language",
                                 aliases='["sql queries"]'))
        db_session.commit()
        profile = _confirmed(client, token)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        sql_topic = next(t for t in topics if t["name"].lower() == "sql queries")
        # The concept alias "sql queries" folds the topic to the canonical name.
        assert sql_topic["normalized_name"] == "structured query language"


class TestReviewLifecycle:
    def test_confirm_reject(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        items = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        tid = items[0]["id"]
        r = client.post(f"/api/subjects/{profile['id']}/topics/{tid}/confirm", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["topic"]["status"] == "confirmed"
        r = client.post(f"/api/subjects/{profile['id']}/topics/{tid}/reject", headers=_auth(token))
        assert r.json()["topic"]["status"] == "rejected"
        # status filter
        q = client.get(f"/api/subjects/{profile['id']}/topics?status=rejected", headers=_auth(token)).json()
        assert q["total"] if "total" in q else len(q["items"]) == 1

    def test_merge(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        items = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        a, b = items[0], items[1]
        r = client.post(
            f"/api/subjects/{profile['id']}/topics/{a['id']}/merge",
            json={"into_topic_id": b["id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        after = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        merged = next(t for t in after if t["id"] == a["id"])
        assert merged["status"] == "merged"

    def test_bloom_fallback(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        items = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        by_name = {t["name"]: t for t in items}
        # "Design database schemas" has design → Create; "Analyze..." → Analyze.
        assert by_name["Design database schemas"]["bloom_level"] == "Create"
        assert by_name["Analyze query performance"]["bloom_level"] == "Analyze"

    def test_per_user_isolation(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token_a = _signup(client, "top-a", "topa@test.com")
        token_b = _signup(client, "top-b", "topb@test.com")
        profile = _confirmed(client, token_a)
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token_a))
        assert client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token_b)).status_code == 404
