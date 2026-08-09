"""Idea 96 — research assistant tests.

Summary reuse, deterministic contribution extraction, related-paper ranking,
cited synthesis, and per-user isolation.
"""
from __future__ import annotations

import pytest

from app.models import KbChunk, KbConcept, KbDocument, KbEdge
from app.services.kb import research as research_service
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="res-user", email="res@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Res", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _paper(db, uid, title, text):
    doc = KbDocument(
        user_id=uid, title=title, extracted_text=text,
        doc_type="pdf", status="ready", char_count=len(text),
    )
    db.add(doc)
    db.flush()
    db.add(KbChunk(
        user_id=uid, document_id=doc.id, seq=0, content=text,
        char_start=0, char_end=len(text), token_estimate=len(text) // 4,
    ))
    db.flush()
    return doc


def _concept(db, uid, name):
    c = KbConcept(user_id=uid, canonical_name=name)
    db.add(c)
    db.flush()
    return c


def _mentions(db, uid, doc, concept):
    db.add(KbEdge(
        user_id=uid, source_document_id=doc.id, target_concept_id=concept.id,
        target_type="concept", relation="MENTIONS",
    ))
    db.flush()


class TestExplain:
    def test_explain_full_flow(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        paper = _paper(
            db_session, uid, "Attention Is All You Need",
            "We introduce the Transformer architecture based solely on attention "
            "mechanisms. It achieves state of the art on translation. "
            "## Contributions\n- Self-attention layers\n- Positional encodings.",
        )
        db_session.commit()

        r = client.post(
            "/api/kb/research/explain",
            json={"document_id": paper.id},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["document_id"] == paper.id
        assert body["summary"] is not None
        # Fallback contributions derive from summary key points.
        assert body["contributions"]
        assert "related" in body

    def test_related_paper_ranking(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        paper = _paper(db_session, uid, "Attention Paper", "Attention mechanisms power transformers.")
        related = _paper(db_session, uid, "Transformer Survey", "Transformers use attention for sequence modeling.")
        unrelated = _paper(db_session, uid, "Quantum Entanglement", "Quantum states cannot be cloned.")
        c = _concept(db_session, uid, "attention")
        _mentions(db_session, uid, paper, c)
        _mentions(db_session, uid, related, c)
        db_session.commit()

        items = research_service.related_papers(db_session, uid, paper.id, limit=5)
        ranked_ids = [i["document_id"] for i in items]
        assert related.id in ranked_ids
        # Shared-concept paper ranks above the unrelated one (or is the only one).
        if unrelated.id in ranked_ids:
            assert ranked_ids.index(related.id) < ranked_ids.index(unrelated.id)

    def test_synthesis_with_question(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        paper = _paper(db_session, uid, "Gradient Paper", "Gradient descent minimizes the loss.")
        db_session.commit()
        result = research_service.synthesize(
            db_session, uid, paper, "what does this paper contribute?"
        )
        assert result["answer"]
        assert "faithfulness_score" in result
        assert "citations" in result


class TestIsolation:
    def test_explain_requires_ownership(self, client, db_session):
        token_a = _signup(client, "res-a", "resa@test.com")
        token_b = _signup(client, "res-b", "resb@test.com")
        paper = _paper(db_session, _uid(token_a), "A's Paper", "A's content.")
        db_session.commit()
        r = client.post(
            "/api/kb/research/explain",
            json={"document_id": paper.id},
            headers=_auth(token_b),
        )
        assert r.status_code == 404
