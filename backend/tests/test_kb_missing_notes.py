"""Idea 77 — missing-note suggestions tests.

Covers the suggest/list lifecycle: concepts the user studies (via user_memory
or the topic graph) but has no note on become suggestions, ranked by gap
evidence; outlines are deterministic; accept creates a pre-filled draft
document + MENTIONS edge; dismiss is permanent (never re-suggested).
"""
from __future__ import annotations

import pytest

from app.models import KbConcept, KbDocument, MissingNoteSuggestion, UserMemory
from app.services.kb import utcnow
from app.services.kb.graph import add_edge


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="miss-user", email="miss@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Miss", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _user_id(db_session, token):
    from app.services.security import decode_bearer_token

    return decode_bearer_token(token)["user_id"]


class TestSuggestion:
    def test_studied_uncovered_concept_suggested(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)

        # Concept the user has memory of (studied) but no document MENTIONS it.
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=3, last_seen=utcnow()))
        db_session.commit()

        r = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items, "expected a missing-note suggestion"
        assert items[0]["concept"] == "Bayesian inference"
        assert items[0]["outline"], "expected a heading outline"
        assert "# Bayesian inference" in items[0]["outline"][0]

    def test_covered_concept_not_suggested(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Linear regression")
        db_session.add(concept)
        db_session.flush()
        doc = KbDocument(user_id=user_id, title="Regression notes", doc_type="md",
                         extracted_text="regression content", status="new")
        db_session.add(doc)
        db_session.flush()
        add_edge(db_session, user_id, doc.id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=1.0)
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()

        items = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"]
        assert not any(i["concept"] == "Linear regression" for i in items)

    def test_reason_mentions_errors(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.3,
                                  exposure_count=1, last_seen=utcnow()))
        db_session.commit()

        items = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"]
        assert items
        assert "no note covering it" in items[0]["reason"]


class TestList:
    def test_list_returns_suggested(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()
        client.post("/api/kb/suggestions/missing-notes", headers=_auth(token))

        items = client.get("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"]
        assert items
        assert items[0]["status"] == "suggested"


class TestAccept:
    def test_accept_creates_draft_note(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()
        suggested = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"][0]

        r = client.post(f"/api/kb/suggestions/{suggested['id']}/accept", headers=_auth(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "accepted"

        doc = db_session.query(KbDocument).get(data["document_id"])
        assert doc is not None
        assert doc.status == "draft"
        assert doc.title == "Bayesian inference"
        assert "## Definition" in doc.extracted_text

        row = db_session.query(MissingNoteSuggestion).get(suggested["id"])
        assert row.status == "accepted"

    def test_accept_twice_400(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()
        suggested = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"][0]
        client.post(f"/api/kb/suggestions/{suggested['id']}/accept", headers=_auth(token))
        r = client.post(f"/api/kb/suggestions/{suggested['id']}/accept", headers=_auth(token))
        assert r.status_code == 400


class TestDismiss:
    def test_dismiss_prevents_resuggestion(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()

        suggested = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"][0]
        r = client.post(f"/api/kb/suggestions/{suggested['id']}/dismiss", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "dismissed"

        # Re-running the generator must not recreate it.
        again = client.post("/api/kb/suggestions/missing-notes", headers=_auth(token)).json()["items"]
        assert not any(i["concept"] == "Bayesian inference" for i in again)


class TestIsolation:
    def test_suggestions_are_per_user(self, client, db_session):
        t_a = _signup(client, "miss-a", "misa@test.com")
        t_b = _signup(client, "miss-b", "misb@test.com")
        user_a = _user_id(db_session, t_a)
        concept = KbConcept(user_id=user_a, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_a, concept_id=concept.id, strength=0.6,
                                  exposure_count=2, last_seen=utcnow()))
        db_session.commit()

        client.post("/api/kb/suggestions/missing-notes", headers=_auth(t_a))
        assert client.get("/api/kb/suggestions/missing-notes", headers=_auth(t_b)).json()["items"] == []
