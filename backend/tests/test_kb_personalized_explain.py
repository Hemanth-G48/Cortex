"""Idea 73 — personalized explanations tests.

Covers the explain_personalized endpoint: anchor selection from user_memory,
style/depth from preferences, prompt rendering (anchors + profile line), the
deterministic fallback when AI is disabled, the inference nudge on follow-up
feedback, and per-user isolation.
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


def _signup(client, uname="pex-user", email="pex@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Pex", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_doc(client, token, tmp_path, text="Gradient descent minimizes the loss function by iterating."):
    (tmp_path / "doc0.md").write_text(text)
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
        headers=_auth(token),
    )
    src = resp.json()
    client.post(f"/api/kb/sources/{src['id']}/scan", headers=_auth(token))


class TestFallback:
    def test_empty_memory_empty_profile_degrades_gracefully(self, client, tmp_path):
        token = _signup(client)
        _seed_doc(client, token, tmp_path)
        r = client.post(
            "/api/kb/explain/personalized",
            json={"concept": "Gradient descent"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fallback"] is True
        assert data["personalized"] is False
        assert data["anchors"] == []
        assert data["explanation"]


class TestAnchors:
    def test_anchors_come_from_memory_only(self, client, db_session, tmp_path):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        _seed_doc(client, token, tmp_path)

        concept = KbConcept(user_id=user_id, canonical_name="linear algebra")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.9,
                                  exposure_count=3, last_seen=utcnow()))
        db_session.commit()

        r = client.post(
            "/api/kb/explain/personalized",
            json={"concept": "Gradient descent"},
            headers=_auth(token),
        )
        data = r.json()
        assert data["anchors"] == ["linear algebra"]
        assert data["personalized"] is True


class TestPromptRendering:
    def test_prompt_contains_anchors_and_profile(self, client, db_session, tmp_path, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        _seed_doc(client, token, tmp_path)

        concept = KbConcept(user_id=user_id, canonical_name="linear algebra")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.9,
                                  exposure_count=3, last_seen=utcnow()))
        db_session.commit()
        client.put("/api/users/me/preferences",
                   json={"onboarding_completed": True, "depth": "deep_dive", "style": "detailed"},
                   headers=_auth(token))

        prompts: list[str] = []

        def fake_generate_json(prompt, **kwargs):
            prompts.append(prompt)
            return {
                "explanation": "Gradient descent iterates. [source: doc0.md]",
                "citations": [1],
            }

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)

        r = client.post(
            "/api/kb/explain/personalized",
            json={"concept": "Gradient descent"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fallback"] is False
        assert prompts, "expected at least one generation"
        joined = prompts[0]
        assert "The student already knows these concepts" in joined
        assert "linear algebra" in joined
        assert "Learning profile" in joined  # onboarding complete → profile line


class TestDepth:
    def test_depth_defaults_to_preference(self, client, db_session, tmp_path, monkeypatch):
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _seed_doc(client, token, tmp_path)
        client.put("/api/users/me/preferences",
                   json={"onboarding_completed": True, "depth": "deep_dive"},
                   headers=_auth(token))

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)

        def fake_generate_json(prompt, **kwargs):
            return {"explanation": "deep dive [source: doc0.md]", "citations": [1]}

        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        r = client.post(
            "/api/kb/explain/personalized",
            json={"concept": "Gradient descent"},
            headers=_auth(token),
        )
        assert r.json()["depth"] == "deep_dive"

    def test_invalid_depth_400(self, client, tmp_path):
        token = _signup(client)
        _seed_doc(client, token, tmp_path)
        r = client.post(
            "/api/kb/explain/personalized",
            json={"concept": "Gradient descent", "depth": "banana"},
            headers=_auth(token),
        )
        assert r.status_code == 400


class TestNudge:
    def test_followup_feedback_nudges_profile(self, client):
        token = _signup(client)
        # Start from a non-default register so the "simpler" nudge visibly
        # changes it (mirrors test_simpler_feedback_nudges_plain_concise).
        client.put(
            "/api/users/me/preferences",
            json={"style": "detailed", "explanation_style": "formal"},
            headers=_auth(token),
        )
        r = client.post("/api/kb/preferences/nudge", json={"feedback": "simpler please"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["provenance"] == "inferred"
        assert "explanation_style" in r.json()["changed"]


class TestBudget:
    def test_explanation_records_generation(self, client, db_session, tmp_path, monkeypatch):
        from app.models import KbGenerationLog
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        _seed_doc(client, token, tmp_path)

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)

        def fake_generate_json(prompt, **kwargs):
            return {"explanation": "Gradient descent iterates. [source: doc0.md]", "citations": [1]}

        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)
        client.post("/api/kb/explain/personalized", json={"concept": "Gradient descent"}, headers=_auth(token))

        kinds = [g.kind for g in db_session.query(KbGenerationLog).filter(KbGenerationLog.user_id == user_id).all()]
        assert "personalized_explain" in kinds


class TestIsolation:
    def test_anchors_are_per_user(self, client, db_session, tmp_path):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        t_a = _signup(client, "pex-a", "pexa@test.com")
        _seed_doc(client, t_a, tmp_path)
        user_a = decode_bearer_token(t_a)["user_id"]
        concept = KbConcept(user_id=user_a, canonical_name="calculus")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_a, concept_id=concept.id, strength=0.9,
                                  exposure_count=3, last_seen=utcnow()))
        db_session.commit()

        # A brand-new user has no memory — no anchors.
        t_b = _signup(client, "pex-b", "pexb@test.com")
        (tmp_path / "doc1.md").write_text("Gradient descent content here.")
        resp = client.post(
            "/api/kb/sources",
            json={"name": "Vault2", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers=_auth(t_b),
        )
        client.post(f"/api/kb/sources/{resp.json()['id']}/scan", headers=_auth(t_b))
        r = client.post("/api/kb/explain/personalized", json={"concept": "Gradient descent"}, headers=_auth(t_b))
        assert r.json()["anchors"] == []
