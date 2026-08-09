"""Idea 71 — learning preference profile tests.

Covers GET/PUT /api/users/me/preferences (validation + clamping), the
preferences_prompt rendering seam shared by tutor + explanations, the
behavioral/feedback inference nudges (provenance=inferred), and per-user
isolation.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="pref-user", email="pref@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Pref", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestCrud:
    def test_defaults_before_set(self, client):
        token = _signup(client)
        r = client.get("/api/users/me/preferences", headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["depth"] == "overview"
        assert data["style"] == "concise"
        assert data["explanation_style"] == "plain"
        assert data["examples_vs_theory"] == 0.5
        assert data["session_length_mins"] == 30
        assert data["onboarding_completed"] is False

    def test_put_updates_and_persists(self, client):
        token = _signup(client)
        r = client.put(
            "/api/users/me/preferences",
            json={
                "depth": "deep_dive",
                "style": "detailed",
                "explanation_style": "analogy",
                "examples_vs_theory": 0.8,
                "session_length_mins": 45,
                "onboarding_completed": True,
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["depth"] == "deep_dive"
        assert data["style"] == "detailed"
        assert data["explanation_style"] == "analogy"
        assert data["session_length_mins"] == 45
        assert data["onboarding_completed"] is True
        # Persisted — a second GET returns the same values.
        again = client.get("/api/users/me/preferences", headers=_auth(token)).json()
        assert again["depth"] == "deep_dive"

    def test_put_partial_keeps_others(self, client):
        token = _signup(client)
        client.put("/api/users/me/preferences", json={"depth": "deep_dive"}, headers=_auth(token))
        client.put("/api/users/me/preferences", json={"style": "detailed"}, headers=_auth(token))
        data = client.get("/api/users/me/preferences", headers=_auth(token)).json()
        assert data["depth"] == "deep_dive"  # not reset by the second partial write
        assert data["style"] == "detailed"


class TestClamping:
    def test_invalid_enums_fall_back_to_defaults(self, client):
        token = _signup(client)
        r = client.put(
            "/api/users/me/preferences",
            json={"depth": "banana", "style": "loud", "explanation_style": "rap"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["depth"] == "overview"
        assert data["style"] == "concise"
        assert data["explanation_style"] == "plain"

    def test_numeric_fields_clamped(self, client):
        token = _signup(client)
        client.put(
            "/api/users/me/preferences",
            json={"examples_vs_theory": 99, "session_length_mins": 5000},
            headers=_auth(token),
        )
        data = client.get("/api/users/me/preferences", headers=_auth(token)).json()
        assert data["examples_vs_theory"] == 1.0
        assert data["session_length_mins"] == 480

        client.put(
            "/api/users/me/preferences",
            json={"examples_vs_theory": -5, "session_length_mins": 0},
            headers=_auth(token),
        )
        data = client.get("/api/users/me/preferences", headers=_auth(token)).json()
        assert data["examples_vs_theory"] == 0.0
        assert data["session_length_mins"] == 1


class TestPromptRendering:
    def test_prompt_empty_until_onboarding(self, client):
        from app.services.kb.preferences import preferences_prompt

        token = _signup(client)
        profile = client.get("/api/users/me/preferences", headers=_auth(token)).json()
        assert preferences_prompt(profile) == ""

    def test_prompt_renders_after_onboarding(self, client):
        from app.services.kb.preferences import preferences_prompt

        token = _signup(client)
        profile = client.put(
            "/api/users/me/preferences",
            json={"onboarding_completed": True, "depth": "deep_dive"},
            headers=_auth(token),
        ).json()
        line = preferences_prompt(profile)
        assert "Learning profile" in line
        assert "depth: deep_dive" in line
        assert "preferred session length" in line

    def test_prompt_none_profile(self):
        from app.services.kb.preferences import preferences_prompt

        assert preferences_prompt(None) == ""


class TestInferenceNudge:
    def test_simpler_feedback_nudges_plain_concise(self, client):
        token = _signup(client)
        # Start from non-default registers so the nudge visibly changes them.
        client.put(
            "/api/users/me/preferences",
            json={"onboarding_completed": True, "style": "detailed", "explanation_style": "formal"},
            headers=_auth(token),
        )
        r = client.post("/api/kb/preferences/nudge", json={"feedback": "Please make it simpler"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["provenance"] == "inferred"
        assert data["changed"]["explanation_style"]["to"] == "plain"
        assert data["changed"]["style"]["to"] == "concise"

    def test_examples_feedback_nudges_slider(self, client):
        token = _signup(client)
        r = client.post("/api/kb/preferences/nudge", json={"feedback": "show me concrete examples"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["changed"]["examples_vs_theory"]["to"] == 0.8

    def test_no_signal_no_change(self, client):
        token = _signup(client)
        r = client.post("/api/kb/preferences/nudge", json={"feedback": "thanks that was useful"}, headers=_auth(token))
        assert r.json()["changed"] == {}

    def test_behavior_nudge_requires_evidence(self, client, db_session):
        from app.services.kb.preferences import nudge_from_behavior

        token = _signup(client)
        from app.services.security import decode_bearer_token

        user_id = decode_bearer_token(token)["user_id"]
        # Fewer than min_sessions events → no-op.
        assert nudge_from_behavior(db_session, user_id)["changed"] == {}

    def test_behavior_nudge_averages_sessions(self, client, db_session):
        from app.models import LearningEvent
        from app.services.kb.preferences import nudge_from_behavior
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        # Average of 10/20/30 = 20 — differs from the 30-min default, so the
        # nudge has something to change.
        for mins in (10, 20, 30):
            db_session.add(LearningEvent(user_id=user_id, event_type="session", value=mins))
        db_session.commit()
        result = nudge_from_behavior(db_session, user_id)
        assert "session_length_mins" in result["changed"]
        assert result["changed"]["session_length_mins"]["to"] == 20


class TestIsolation:
    def test_preferences_are_per_user(self, client):
        t_a = _signup(client, "pref-a", "prefa@test.com")
        t_b = _signup(client, "pref-b", "prefb@test.com")
        client.put("/api/users/me/preferences", json={"depth": "deep_dive"}, headers=_auth(t_a))
        b = client.get("/api/users/me/preferences", headers=_auth(t_b)).json()
        assert b["depth"] == "overview"
        a = client.get("/api/users/me/preferences", headers=_auth(t_a)).json()
        assert a["depth"] == "deep_dive"
