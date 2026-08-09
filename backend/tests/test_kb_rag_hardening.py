"""Idea 93 — full RAG pipeline hardening tests.

Stage composition, deterministic rerank ordering, citation verification,
faithfulness gating, and the ungrounded "not found" fallback.
"""
from __future__ import annotations

import pytest

from app.services.kb import rag
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _uid(token) -> int:
    return decode_bearer_token(token)["user_id"]


def _signup(client, uname="rag-user", email="rag@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Rag", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _doc(db, uid, title, text):
    from app.models import KbChunk, KbDocument

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
    db.commit()
    return doc


class TestStages:
    def test_rewrite_returns_both_queries(self, client, db_session):
        token = _signup(client)
        _doc(db_session, _uid(token), "Gradient Descent Notes",
             "Gradient descent is an optimization algorithm used to minimize loss functions.")
        rw = rag.rewrite_query(db_session, _uid(token), "gradient descent")
        assert rw["original_query"] == "gradient descent"
        assert isinstance(rw["expanded_query"], str)

    def test_stage_timing_in_pipeline(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _doc(db_session, uid, "T", "Newton's laws of motion define classical mechanics.")
        result = rag.run_pipeline(db_session, uid, "newton laws", generate=False)
        assert "stage_times_ms" in result
        for key in ("rewrite_ms", "retrieve_ms", "rerank_ms"):
            assert key in result["stage_times_ms"]
        assert result["original_query"] == "newton laws"


class TestRerank:
    def test_deterministic_rerank_prefers_overlap(self):
        items = [
            {"chunk_id": 1, "title": "photosynthesis", "snippet": "plants make food from sunlight", "score": 0.9},
            {"chunk_id": 2, "title": "mitochondria", "snippet": "cell powerhouse atp", "score": 0.99},
        ]
        ranked = rag.rerank(None, 1, items, "photosynthesis food")  # type: ignore[arg-type]
        assert ranked[0]["chunk_id"] == 1

    def test_rerank_empty_is_safe(self):
        assert rag.rerank(None, 1, [], "query") == []  # type: ignore[arg-type]


class TestCitations:
    def test_verify_citations_maps_claims(self):
        items = [
            {"chunk_id": 10, "document_id": 5, "title": "A", "source_path": "a.md"},
            {"chunk_id": 11, "document_id": 6, "title": "B", "source_path": "b.md"},
        ]
        # Citation markers are chunk ids: [10] and [11] (not ordinal 1, 2).
        result = rag.verify_citations("See [10] and [11] for details", items)
        assert {c["chunk_id"] for c in result["citations"]} == {10, 11}
        assert result["cited_chunk_ids"] == [10, 11]

    def test_verify_no_items(self):
        result = rag.verify_citations("no sources", [])
        assert result["citations"] == []
        assert result["cited_chunk_ids"] == []


class TestFaithfulness:
    def test_cited_answer_scores_high(self):
        items = [{"chunk_id": 1, "snippet": "Gradient descent minimizes the loss function iteratively."}]
        score = rag.faithfulness("Gradient descent minimizes loss iteratively [source: a.md]", items)
        assert score >= 0.4

    def test_ungrounded_scores_low(self):
        items = [{"chunk_id": 1, "snippet": "photosynthesis converts sunlight to energy."}]
        score = rag.faithfulness("The moon is made of cheese and there is no other truth", items)
        assert score < 0.4

    def test_generate_grounded_not_found(self, db_session):
        result = rag.generate_grounded(db_session, 1, "quantum gravity", [])
        assert "Not found" in result["answer"]
        assert result["faithfulness_score"] == 0.0
        assert result["ai_used"] is False

    def test_generate_grounded_deterministic_fallback(self, client, db_session):
        token = _signup(client)
        uid = _uid(token)
        _doc(db_session, uid, "Photosynthesis",
             "Photosynthesis converts light into chemical energy.")
        items = rag.retrieve(db_session, uid, "photosynthesis", limit=3)
        result = rag.generate_grounded(db_session, uid, "what is photosynthesis", items)
        assert result["ai_used"] is False
        assert "notes say" in result["answer"] or "Not found" in result["answer"]


class TestIsolation:
    def test_pipeline_scopes_to_user(self, client, db_session):
        uid_a = _uid(_signup(client, "rag-a", "raga@test.com"))
        uid_b = _uid(_signup(client, "rag-b", "ragb@test.com"))
        _doc(db_session, uid_a, "For User A",
             "The quadratic formula solves ax^2 + bx + c = 0.")
        _doc(db_session, uid_b, "For User B",
             "The quadratic formula solves ax^2 + bx + c = 0.")
        result = rag.run_pipeline(db_session, uid_a, "quadratic formula", generate=False)
        assert result["items"]
        # User A's retrieval only returns A's documents.
        from app.models import KbDocument

        for item in result["items"]:
            row = db_session.get(KbDocument, item["document_id"])
            assert row.user_id == uid_a
