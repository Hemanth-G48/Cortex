"""Auto-flashcard candidate job tests (Phase 9, Idea 85, phrases 41-50)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import KbChunk, KbConcept, KbDocument, KbEdge, KbFlashcardCandidate, User
from app.services.kb.auto_flashcards import run

AUTH = "Authorization"


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Auto tests are deterministic: candidates come from the concept fallback."""
    from app.config import settings

    monkeypatch.setattr(settings, "AI_ENABLED", False)


def _signup(client: TestClient, uname: str = "flash-auto", email: str = "flashauto@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Flasher",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "flashauto@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(db: Session, user_id: int, title: str = "Note") -> KbDocument:
    content = f"# {title}\n\nGradient descent minimizes the loss function by iterating."
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=f"{title}.md",
        extracted_text=content,
        content_hash=f"hash-{title}",
        char_count=len(content),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.add(
        KbChunk(
            user_id=user_id,
            document_id=doc.id,
            seq=0,
            content=content,
            char_start=0,
            char_end=len(content),
            token_estimate=10,
        )
    )
    db.commit()
    return doc


def _add_concept(db: Session, user_id: int, doc: KbDocument, name: str = "gradient descent") -> KbConcept:
    concept = KbConcept(user_id=user_id, canonical_name=name)
    db.add(concept)
    db.commit()
    db.refresh(concept)
    db.add(
        KbEdge(
            user_id=user_id,
            source_document_id=doc.id,
            relation="MENTIONS",
            target_type="concept",
            target_concept_id=concept.id,
            weight=0.9,
        )
    )
    db.commit()
    return concept


class TestRun:
    def test_concept_bearing_doc_gets_auto_candidates(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)
        _add_concept(db_session, uid, doc)

        summary = run(db_session, uid)
        assert summary["processed"] == 1
        assert summary["generated"] >= 1

        rows = (
            db_session.query(KbFlashcardCandidate)
            .filter(KbFlashcardCandidate.document_id == doc.id)
            .all()
        )
        assert len(rows) >= 1
        assert all(r.source == "auto" for r in rows)
        assert all(r.status == "pending" for r in rows)

    def test_skips_docs_without_concepts(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="Plain")

        summary = run(db_session, uid)
        assert summary["processed"] == 0
        assert summary["generated"] == 0

    def test_skips_already_carded_docs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)
        _add_concept(db_session, uid, doc)

        first = run(db_session, uid)
        second = run(db_session, uid)
        assert first["processed"] == 1
        assert second["processed"] == 0  # already has candidates → idempotent

    def test_approve_flows_to_deck(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)
        _add_concept(db_session, uid, doc)
        run(db_session, uid)

        cand = (
            db_session.query(KbFlashcardCandidate)
            .filter(KbFlashcardCandidate.document_id == doc.id)
            .first()
        )
        assert cand is not None

        resp = client.post(
            "/api/kb/flashcards/review",
            json={"approve": [cand.id]},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        # Cards were committed into the default deck.
        from app.models import Flashcard

        cards = db_session.query(Flashcard).all()
        assert len(cards) >= 1

    def test_respects_limit(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        for t in ("A", "B", "C"):
            doc = _make_doc(db_session, uid, title=t)
            _add_concept(db_session, uid, doc, name=f"concept-{t}")

        summary = run(db_session, uid, limit=2)
        assert summary["processed"] == 2

    def test_user_isolation(self, db_session: Session, client: TestClient):
        _signup(client, uname="fa-a", email="faa@test.com")
        _signup(client, uname="fa-b", email="fab@test.com")
        uid_a = _uid(db_session, "faa@test.com")
        uid_b = _uid(db_session, "fab@test.com")
        doc_a = _make_doc(db_session, uid_a, title="A")
        _add_concept(db_session, uid_a, doc_a)

        summary = run(db_session, uid_b)
        assert summary["processed"] == 0


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)
        _add_concept(db_session, uid, doc)

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_flashcards", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_flashcards"
        assert resp.json()["status"] == "done"

        rows = (
            db_session.query(KbFlashcardCandidate)
            .filter(KbFlashcardCandidate.document_id == doc.id)
            .all()
        )
        assert len(rows) >= 1
