"""Auto-duplicate tests (Phase 9, Idea 84, phrases 31-40)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument, KbEdge, KbEmbedding, User
from app.services.kb.auto_duplicates import run

AUTH = "Authorization"

# Cosine targets vs KB_NEARDUP_THRESHOLD (0.95).
V_DUPLICATE = [1.0, 0.0]  # cosine 1.0 with itself → duplicate
V_ORTHOGONAL = [0.0, 1.0]  # cosine 0 → not a duplicate


def _signup(client: TestClient, uname: str = "dupe-user", email: str = "dupe@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Duper",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "dupe@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(db: Session, user_id: int, vec: list[float], title: str) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=f"{title}.md",
        extracted_text=f"# {title}\n\ncontent {title}",
        content_hash=f"hash-{title}",
        char_count=30,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    chunk = KbChunk(
        user_id=user_id,
        document_id=doc.id,
        seq=0,
        content=doc.extracted_text,
        token_estimate=10,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    db.add(
        KbEmbedding(
            user_id=user_id,
            chunk_id=chunk.id,
            vector=json.dumps(vec),
            model="test",
            dim=len(vec),
        )
    )
    db.commit()
    return doc


def _duplicate_edges(db: Session, user_id: int) -> list[KbEdge]:
    # Only cross-document pair edges count — self-loops (the canonical doc's
    # dedupe counter) are excluded, matching ``list_duplicates`` semantics.
    return (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DUPLICATE_OF",
            KbEdge.source_document_id != KbEdge.target_document_id,
        )
        .all()
    )


class TestRun:
    def test_records_near_duplicate_pair(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_DUPLICATE, "A")
        _make_doc(db_session, uid, V_DUPLICATE, "B")

        summary = run(db_session, uid)
        assert summary["duplicates"] == 1

        edges = _duplicate_edges(db_session, uid)
        assert len(edges) == 1
        assert edges[0].provenance == "auto"
        # The later (higher id) doc is the duplicate source.
        assert edges[0].source_document_id > edges[0].target_document_id

    def test_skips_orthogonal_docs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_DUPLICATE, "A")
        _make_doc(db_session, uid, V_ORTHOGONAL, "B")

        summary = run(db_session, uid)
        assert summary["duplicates"] == 0
        assert _duplicate_edges(db_session, uid) == []

    def test_idempotent_across_runs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_DUPLICATE, "A")
        _make_doc(db_session, uid, V_DUPLICATE, "B")
        _make_doc(db_session, uid, V_DUPLICATE, "C")

        first = run(db_session, uid)
        second = run(db_session, uid)
        assert first["duplicates"] == 3  # AB, AC, BC
        assert second["duplicates"] == 0  # all already linked

    def test_respects_limit(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_DUPLICATE, "A")
        _make_doc(db_session, uid, V_DUPLICATE, "B")
        _make_doc(db_session, uid, V_DUPLICATE, "C")

        summary = run(db_session, uid, limit=2)
        assert summary["duplicates"] == 2


class TestEndpoints:
    def test_force_run_surfaces_in_duplicate_queue(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_DUPLICATE, "A")
        _make_doc(db_session, uid, V_DUPLICATE, "B")

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_duplicates", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_duplicates"
        assert resp.json()["status"] == "done"

        # The existing duplicate review queue surfaces the pair.
        dup = client.get("/api/kb/duplicates", headers={AUTH: f"Bearer {token}"})
        assert dup.status_code == 200, dup.text
        assert dup.json()["total"] >= 1
