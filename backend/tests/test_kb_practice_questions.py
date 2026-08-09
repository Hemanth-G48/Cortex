"""Idea 63 — AI-generated practice questions tests.

Covers generation into a reviewable bank (pending only, nothing auto-committed),
question-hash dedupe, approve/reject lifecycle into the reusable bank, mock-LLM
generation shape, deterministic fallback, and per-user isolation.
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


def _signup(client, uname="pq-user", email="pq@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "PQ", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _first_topic(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topic = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"][0]
    return profile, topic


class TestGenerate:
    def test_generate_creates_pending_candidates(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 5, "difficulty": "M"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] == 5
        items = data["items"]
        assert all(i["status"] == "pending" for i in items)
        assert all(i["topic_id"] == topic["id"] for i in items)
        assert all(len(i["options"]) >= 2 for i in items)
        assert all(i["difficulty"] == "M" for i in items)

    def test_dedupe_by_question_hash(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        first = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 4, "difficulty": "M"},
            headers=_auth(token),
        ).json()
        # Deterministic fallback produces identical questions → all deduped.
        second = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 4, "difficulty": "M"},
            headers=_auth(token),
        ).json()
        assert second["generated"] == 0
        assert len(first["items"]) == 4

    def test_generate_unknown_topic_404(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": 9999},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_mock_llm_generation(self, client, monkeypatch):
        token = _signup(client)
        _, topic = _first_topic(client, token)

        def fake_generate_json(prompt, **kwargs):
            return {
                "questions": [
                    {"q": "Which loss is used for regression?", "options": [
                        "MSE", "Cross-entropy", "Hinge", "Focal"],
                     "answer": "MSE", "explanation": "Regression targets are continuous.",
                     "bloom_level": "Understand", "difficulty": "M"},
                    {"q": "What does gradient descent minimize?", "options": [
                        "Loss", "Accuracy", "Overfitting", "Bias"],
                     "answer": "Loss", "explanation": "It follows the gradient of the loss.",
                     "bloom_level": "Remember", "difficulty": "E"},
                ]
            }

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        r = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 2},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == 2
        assert {i["bloom_level"] for i in items} == {"Understand", "Remember"}


class TestReviewLifecycle:
    def test_approve_reject(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        items = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 3},
            headers=_auth(token),
        ).json()["items"]
        assert len(items) == 3
        q1, q2 = items[0]["id"], items[1]["id"]

        r = client.post(f"/api/kb/practice/{q1}/approve", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["question"]["status"] == "approved"

        r = client.post(f"/api/kb/practice/{q2}/reject", headers=_auth(token))
        assert r.json()["question"]["status"] == "rejected"

    def test_list_filters_by_status(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 3},
            headers=_auth(token),
        )
        pending = client.get("/api/kb/practice/questions?status=pending", headers=_auth(token)).json()["items"]
        assert len(pending) == 3
        approved = client.get("/api/kb/practice/questions?status=approved", headers=_auth(token)).json()["items"]
        assert approved == []

    def test_approve_other_users_question_404(self, client):
        t_a = _signup(client, "pq-a", "pqa@test.com")
        t_b = _signup(client, "pq-b", "pqb@test.com")
        _, topic = _first_topic(client, t_a)
        qid = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 1},
            headers=_auth(t_a),
        ).json()["items"][0]["id"]
        r = client.post(f"/api/kb/practice/{qid}/approve", headers=_auth(t_b))
        assert r.status_code == 404


class TestFallback:
    def test_fallback_shape(self, client):
        # AI disabled → template questions per Bloom level (phrase 27).
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            "/api/kb/practice/generate",
            json={"topic_id": topic["id"], "count": 3},
            headers=_auth(token),
        )
        items = r.json()["items"]
        assert len(items) == 3
        assert all(i["explanation"] for i in items)
        blooms = {i["bloom_level"] for i in items}
        assert len(blooms) >= 2
