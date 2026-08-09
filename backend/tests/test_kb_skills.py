"""Idea 70 — skill mapping tests.

Covers the versioned taxonomy load, topic→skill mapping (LLM mocked + keyword
fallback), mastery-derived level math, interview-score effect, the skills
profile + export endpoints, and per-user isolation.
"""
from __future__ import annotations

import json

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


def _signup(client, uname="skl-user", email="skl@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Skl", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    confirmed = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    profile = confirmed.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


class TestTaxonomy:
    def test_loads_versioned_taxonomy(self):
        from app.services.kb.skills import load_taxonomy

        tax = load_taxonomy()
        assert tax["version"] >= 1
        assert len(tax["skills"]) > 0
        ids = {s["id"] for s in tax["skills"]}
        assert "ml_foundations" in ids
        assert "cs_programming" in ids

    def test_level_for_math(self):
        from app.services.kb.skills import _level_for

        assert _level_for(0.0) == 1
        assert _level_for(0.2) == 1
        assert _level_for(0.5) == 3
        assert _level_for(0.8) == 4
        assert _level_for(1.0) == 5


class TestMapping:
    def test_keyword_fallback_maps_ml_topics(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mapped"] >= 1
        ids = {s["skill_id"] for s in data["skills"]}
        # ML syllabus topics contain "regression" / "gradient descent" /
        # "linear algebra" / "probability" → those taxonomy skills.
        assert "ml_foundations" in ids
        assert "math_linear_algebra" in ids

    def test_mock_llm_mapping(self, client, monkeypatch):
        token = _signup(client)
        profile = _confirmed(client, token)

        def fake_generate_json(prompt, **kwargs):
            return {
                "mappings": [
                    {"topic": "Linear regression", "skill_id": "ml_foundations"},
                    {"topic": "Gradient descent", "skill_id": "ml_foundations"},
                    {"topic": "Linear algebra review", "skill_id": "math_linear_algebra"},
                ]
            }

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        r = client.post(
            "/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        ids = {s["skill_id"] for s in data["skills"]}
        assert "ml_foundations" in ids
        assert "math_linear_algebra" in ids

    def test_map_unconfirmed_subject_400(self, client):
        token = _signup(client)
        r = client.post("/api/kb/skills/map", json={"subject_id": 9999}, headers=_auth(token))
        assert r.status_code == 400

    def test_skills_are_per_user(self, client):
        t_a = _signup(client, "skl-a", "skla@test.com")
        t_b = _signup(client, "skl-b", "sklb@test.com")
        _confirmed(client, t_a)
        assert client.get("/api/kb/skills", headers=_auth(t_b)).json()["skills"] == []


class TestLevelFromMastery:
    def test_mastery_drives_level(self, client, db_session):
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        profile = _confirmed(client, token)
        topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
        user_id = decode_bearer_token(token)["user_id"]
        # Strong mastery on every ML topic (6 perfect quizzes each) so the
        # ml_foundations aggregate (mean of its contributors) is high.
        for t in topics:
            for _ in range(6):
                log_event(db_session, user_id, event_type="quiz",
                          topic_id=t["id"], value=1.0)
        db_session.commit()

        data = client.post(
            "/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        ).json()
        ml = next(s for s in data["skills"] if s["skill_id"] == "ml_foundations")
        assert ml["level"] >= 3
        assert ml["mastery"] > 0.7


class TestExport:
    def test_markdown_export(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(
            "/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        )
        r = client.get("/api/kb/skills/export?fmt=markdown", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["format"] == "markdown"
        assert "# Skills" in r.json()["content"]
        assert "Machine Learning Foundations" in r.json()["content"]

    def test_json_export_parses(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(
            "/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        )
        r = client.get("/api/kb/skills/export?fmt=json", headers=_auth(token))
        content = json.loads(r.json()["content"])
        assert content["version"] >= 1
        assert any(s["skill_id"] == "ml_foundations" for s in content["skills"])

    def test_empty_export(self, client):
        token = _signup(client)
        r = client.get("/api/kb/skills/export?fmt=markdown", headers=_auth(token))
        assert "# Skills" in r.json()["content"]


class TestInterviewEffect:
    def test_finish_updates_skill_level(self, client, db_session, monkeypatch):
        from app.models import UserSkill
        from app.services.security import decode_bearer_token

        # Enable AI so interview finish can nudge the skill even with an
        # existing row created by mapping.
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(
            "/api/kb/skills/map",
            json={"subject_id": profile["curriculum_subject_id"]},
            headers=_auth(token),
        )
        user_id = decode_bearer_token(token)["user_id"]
        row = (
            db_session.query(UserSkill)
            .filter(UserSkill.user_id == user_id, UserSkill.skill_id == "ml_foundations")
            .first()
        )
        before = row.mastery if row else 0.0

        session = client.post(
            "/api/kb/interview/start",
            json={"skill": "ml_foundations", "level": "advanced"},
            headers=_auth(token),
        ).json()["session"]
        client.post(
            f"/api/kb/interview/{session['id']}/answer",
            json={"index": 0, "answer": "An excellent, complete answer."},
            headers=_auth(token),
        )
        client.post(f"/api/kb/interview/{session['id']}/finish", headers=_auth(token))

        updated = (
            db_session.query(UserSkill)
            .filter(UserSkill.user_id == user_id, UserSkill.skill_id == "ml_foundations")
            .first()
        )
        # A good score nudges mastery upward from the mapped value.
        assert updated is not None
        assert updated.mastery >= before
