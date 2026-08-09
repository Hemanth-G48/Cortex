"""Idea 94 — knowledge-graph + vector fusion tests.

Expansion correctness over kb_edges, dedupe, cap enforcement, the
``mode=graph_fused`` search endpoint, prerequisite chains, and per-user
isolation.
"""
from __future__ import annotations

import pytest

from app.models import KbConcept, KbDocument, KbEdge
from app.services.kb import fusion
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="fus-user", email="fus@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Fus", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _doc(db, uid, title, text="content here"):
    from app.models import KbChunk

    doc = KbDocument(
        user_id=uid, title=title, extracted_text=text,
        doc_type="md", status="ready", char_count=len(text),
    )
    db.add(doc)
    db.flush()
    # A chunk so the FTS index can actually match the text.
    db.add(KbChunk(
        user_id=uid, document_id=doc.id, seq=0, content=text,
        char_start=0, char_end=len(text), token_estimate=len(text) // 4,
    ))
    db.flush()
    return doc


def _edge(db, uid, src, tgt, relation="RELATED", weight=0.9):
    db.add(KbEdge(
        user_id=uid, source_document_id=src.id, target_document_id=tgt.id,
        relation=relation, weight=weight,
    ))
    db.flush()


class TestExpansion:
    def test_expands_via_related_edges(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        a = _doc(db_session, uid, "Linear Regression Notes")
        b = _doc(db_session, uid, "Gradient Descent Notes")
        _edge(db_session, uid, a, b, "RELATED")
        db_session.commit()

        hits = [
            {"chunk_id": 1, "document_id": a.id, "title": a.title, "snippet": "x",
             "score": 0.9, "source_path": "a.md", "heading_path": None,
             "doc_type": "md", "doc_date": None, "char_start": 0, "char_end": 1},
        ]
        expanded = fusion.graph_expand(db_session, uid, hits, hops=1, cap=5)
        added = [e for e in expanded if e["document_id"] == b.id]
        assert added
        assert any("graph:" in (s or "") for s in added[0]["sources"])

    def test_dedupe_and_cap(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        a = _doc(db_session, uid, "A")
        b = _doc(db_session, uid, "B")
        c = _doc(db_session, uid, "C")
        _edge(db_session, uid, a, b, "RELATED")
        _edge(db_session, uid, a, c, "RELATED")
        _edge(db_session, uid, b, c, "SHARES_CONCEPT")
        db_session.commit()

        hits = [{"chunk_id": 1, "document_id": a.id, "title": "A", "snippet": "",
                 "score": 0.9, "source_path": None, "heading_path": None,
                 "doc_type": "md", "doc_date": None, "char_start": 0, "char_end": 0}]
        # Cap of 1 added candidate.
        expanded = fusion.graph_expand(db_session, uid, hits, hops=2, cap=1)
        added = [e for e in expanded if e["document_id"] != a.id]
        assert len(added) == 1
        # No duplicates of the original hit.
        assert sum(1 for e in expanded if e["document_id"] == a.id) == 1

    def test_prerequisite_chains(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        a = _doc(db_session, uid, "Calculus Foundations")
        b = _doc(db_session, uid, "Optimization")
        _edge(db_session, uid, a, b, "DEPENDS_ON")
        db_session.commit()
        chains = fusion.prerequisite_chains(db_session, uid, [b.id])
        assert len(chains) == 1
        assert "Calculus Foundations" in chains[0]
        assert "prerequisite" in chains[0]

    def test_cap_zero_is_noop(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        a = _doc(db_session, uid, "A")
        b = _doc(db_session, uid, "B")
        _edge(db_session, uid, a, b, "RELATED")
        db_session.commit()
        hits = [{"chunk_id": 1, "document_id": a.id, "title": "A", "snippet": "",
                 "score": 0.9, "source_path": None, "heading_path": None,
                 "doc_type": "md", "doc_date": None, "char_start": 0, "char_end": 0}]
        assert len(fusion.graph_expand(db_session, uid, hits, cap=0)) == 1


class TestSearchMode:
    def test_search_graph_fused_mode(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        a = _doc(db_session, uid, "Photosynthesis Notes",
                 "Photosynthesis converts light into chemical energy in plants.")
        b = _doc(db_session, uid, "Chloroplast Structure",
                 "Chloroplasts are where photosynthesis happens in plant cells.")
        _edge(db_session, uid, a, b, "RELATED")
        db_session.commit()

        r = client.post(
            "/api/kb/search",
            json={"query": "photosynthesis", "mode": "graph_fused", "page_size": 10},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "graph_fused"
        found_ids = {i["document_id"] for i in body["items"]}
        assert a.id in found_ids

    def test_isolation(self, client, db_session):
        uid_a = _uid(_signup(client, "fus-a", "fusa@test.com"))
        uid_b = _uid(_signup(client, "fus-b", "fusb@test.com"))
        a = _doc(db_session, uid_a, "A-Only")
        b = _doc(db_session, uid_b, "B-Only")
        _edge(db_session, uid_a, a, _doc(db_session, uid_a, "A2"), "RELATED")
        _edge(db_session, uid_b, b, _doc(db_session, uid_b, "B2"), "RELATED")
        db_session.commit()

        hits = [{"chunk_id": 1, "document_id": a.id, "title": "A-Only", "snippet": "",
                 "score": 0.9, "source_path": None, "heading_path": None,
                 "doc_type": "md", "doc_date": None, "char_start": 0, "char_end": 0}]
        expanded = fusion.graph_expand(db_session, uid_a, hits, hops=2, cap=10)
        doc_ids = {e["document_id"] for e in expanded}
        assert b.id not in doc_ids
