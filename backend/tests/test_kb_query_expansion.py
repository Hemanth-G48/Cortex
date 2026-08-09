"""Idea 24 — query expansion tests.

Covers normalization, alias/abbreviation expansion from kb_concepts, the
static abbreviation table, and the short-query 400 guard on the endpoint.
LLM rewrite is guarded behind AI_ENABLED (mocked-off here) so tests stay
hermetic.
"""
from __future__ import annotations

import json

from app.services.kb import query as qs


def _signup(client, uname="qe-user", email="qe@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "QE", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _mk_db(db_session, user_id):
    """Seed a concept with aliases into the shared session."""
    from app.models import KbConcept
    db_session.add(KbConcept(
        user_id=user_id,
        canonical_name="Machine Learning",
        definition="A field of AI.",
        aliases=json.dumps(["ML", "ml"]),
    ))
    db_session.commit()
    return db_session


class TestNormalization:
    def test_normalize(self):
        assert qs._normalize("  Deep   Learning! ") == "deep learning"
        assert qs._normalize("C++ and Rust") == "c and rust"

    def test_expand_empty_returns_original(self, db_session):
        assert qs.expand(db_session, 1, "") == ""


class TestAliasExpansion:
    def test_concept_alias_expands(self, db_session):
        # Needs a real user for the concept FK.
        from app.models import User
        u = User(name="x", username="qe-1", email="qe1@test.com",
                 password_hash="h", role="student")
        db_session.add(u)
        db_session.flush()
        _mk_db(db_session, u.id)

        out = qs.expand(db_session, u.id, "ML is powerful")
        # "ML" is an alias for machine learning → canonical name included.
        assert "machine learning" in out

    def test_abbreviation_expansion(self, db_session):
        from app.models import User
        u = User(name="x", username="qe-2", email="qe2@test.com",
                 password_hash="h", role="student")
        db_session.add(u)
        db_session.flush()
        out = qs.expand(db_session, u.id, "nlp techniques")
        # "nlp" → "natural language processing" from the static table.
        assert "natural language processing" in out


class TestEndpointGuard:
    def test_short_query_400(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/kb/search",
            json={"query": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (400, 422)
