"""Idea 72 — concept-level knowledge-gap detection tests.

Covers error→concept mapping (quiz events), retrieval-miss incorporation
(kb_search_events), the composite gap formula, ranked output with evidence +
capture sources, and per-user isolation.
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


def _signup(client, uname="gap-user", email="gap@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Gap", "username": uname, "email": email,
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


class TestErrorMapping:
    def test_quiz_errors_map_to_concepts(self, client, db_session):
        from app.services.kb.mastery import log_event
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]

        from app.models import KbConcept, Topic

        topics_all = db_session.query(Topic).filter(Topic.user_id == user_id).all()
        reg = next(t for t in topics_all if t.name == "Linear regression")
        concept = KbConcept(user_id=user_id, canonical_name="Linear regression")
        db_session.add(concept)
        db_session.commit()

        # Two wrong quiz attempts on the regression topic.
        log_event(db_session, user_id, event_type="quiz", topic_id=reg.id, value=0.2)
        log_event(db_session, user_id, event_type="quiz", topic_id=reg.id, value=0.3)
        db_session.commit()

        r = client.get("/api/kb/gaps/concepts", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        gap = next(g for g in items if g["concept_id"] == concept.id)
        assert gap["evidence"]["quiz_errors"] >= 2
        assert gap["score"] > 0


class TestRetrievalMisses:
    def test_missed_searches_flag_concepts(self, client, db_session):
        from app.models import KbConcept, KbSearchEvent
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="Maximum Likelihood", aliases=json.dumps(["MLE"]))
        db_session.add(concept)
        db_session.commit()

        # User searched for it and got nothing back (empty result_ids).
        db_session.add(KbSearchEvent(user_id=user_id, query="MLE", mode="hybrid", result_ids=json.dumps([])))
        db_session.add(KbSearchEvent(user_id=user_id, query="maximum likelihood", mode="hybrid", result_ids=json.dumps([])))
        db_session.add(KbSearchEvent(user_id=user_id, query="other thing", mode="hybrid", result_ids=json.dumps([1, 2, 3])))
        db_session.commit()

        items = client.get("/api/kb/gaps/concepts", headers=_auth(token)).json()["items"]
        gap = next(g for g in items if g["concept_id"] == concept.id)
        assert gap["evidence"]["retrieval_misses"] == 2


class TestFormula:
    def test_known_strong_concept_scores_low(self, client, db_session):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="Gradient descent")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.9,
                                  exposure_count=12, last_seen=utcnow()))
        db_session.commit()

        items = client.get("/api/kb/gaps/concepts", headers=_auth(token)).json()["items"]
        gap = next(g for g in items if g["concept_id"] == concept.id)
        # High strength → the memory component (1 - strength) is small.
        assert gap["evidence"]["strength"] == 0.9
        assert gap["score"] < 0.3

    def test_never_met_concept_ranks_first(self, client, db_session):
        from app.models import KbConcept
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="Bayesian inference")
        db_session.add(concept)
        db_session.commit()

        items = client.get("/api/kb/gaps/concepts", headers=_auth(token)).json()["items"]
        gap = next(g for g in items if g["concept_id"] == concept.id)
        assert gap["evidence"]["strength"] == 0.0
        assert gap["score"] > 0.3


class TestSources:
    def test_mention_sources_listed(self, client, db_session):
        from app.models import KbConcept, KbDocument, KbEdge
        from app.services.kb.graph import add_edge
        from app.services.security import decode_bearer_token

        token = _signup(client)
        _confirmed(client, token)
        user_id = decode_bearer_token(token)["user_id"]
        concept = KbConcept(user_id=user_id, canonical_name="Probability review")
        db_session.add(concept)
        db_session.flush()
        doc = KbDocument(user_id=user_id, title="Probability notes", doc_type="md",
                         extracted_text="probability content", status="new")
        db_session.add(doc)
        db_session.flush()
        add_edge(db_session, user_id, doc.id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9, overwrite=True)
        db_session.commit()

        items = client.get("/api/kb/gaps/concepts", headers=_auth(token)).json()["items"]
        gap = next(g for g in items if g["concept_id"] == concept.id)
        assert gap["sources"], "expected capture sources"
        assert gap["sources"][0]["document_id"] == doc.id


class TestIsolation:
    def test_gaps_are_per_user(self, client, db_session):
        from app.models import KbConcept
        from app.services.security import decode_bearer_token

        t_a = _signup(client, "gap-a", "gapa@test.com")
        t_b = _signup(client, "gap-b", "gapb@test.com")
        _confirmed(client, t_a)
        user_a = decode_bearer_token(t_a)["user_id"]
        db_session.add(KbConcept(user_id=user_a, canonical_name="Quantum mechanics"))
        db_session.commit()

        a_items = client.get("/api/kb/gaps/concepts", headers=_auth(t_a)).json()["items"]
        b_items = client.get("/api/kb/gaps/concepts", headers=_auth(t_b)).json()["items"]
        assert any(g["concept"] == "Quantum mechanics" for g in a_items)
        assert not any(g["concept"] == "Quantum mechanics" for g in b_items)


class TestEmpty:
    def test_empty_vault_returns_empty(self, client):
        token = _signup(client)
        assert client.get("/api/kb/gaps/concepts", headers=_auth(token)).json()["items"] == []
