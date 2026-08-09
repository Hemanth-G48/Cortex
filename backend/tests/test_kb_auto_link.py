"""Auto-link tests (Phase 9, Idea 83, phrases 21-30)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument, KbEdge, KbEmbedding, User
from app.services.kb.auto_link import accept, queue, reject, run

AUTH = "Authorization"

# Cosine targets (2-dim vectors, zero-padded to EMBEDDINGS_DIM by the service).
V_IDENTICAL = [1.0, 0.0]
V_MODERATE = [0.8, 0.6]  # cosine 0.8 with V_IDENTICAL → pending band
V_DISSIMILAR = [0.0, 1.0]  # cosine 0 with V_IDENTICAL → nothing


def _signup(client: TestClient, uname: str = "link-user", email: str = "link@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Linker",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "link@test.com") -> int:
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


def _edges(db: Session, user_id: int) -> list[KbEdge]:
    return (
        db.query(KbEdge)
        .filter(KbEdge.user_id == user_id)
        .order_by(KbEdge.id.asc())
        .all()
    )


class TestRun:
    def test_identical_docs_auto_link(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_IDENTICAL, "B")

        summary = run(db_session, uid)
        assert summary["linked"] == 1
        assert summary["proposed"] == 0

        edges = _edges(db_session, uid)
        assert len(edges) == 1
        assert edges[0].status == "active"
        assert edges[0].weight == 1.0

    def test_moderate_similarity_proposes(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_MODERATE, "B")

        summary = run(db_session, uid)
        assert summary["linked"] == 0
        assert summary["proposed"] == 1

        edges = _edges(db_session, uid)
        assert len(edges) == 1
        assert edges[0].status == "pending"
        assert 0.75 <= edges[0].weight < 0.88

    def test_dissimilar_docs_no_edge(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_DISSIMILAR, "B")

        summary = run(db_session, uid)
        assert summary["linked"] == 0
        assert summary["proposed"] == 0
        assert _edges(db_session, uid) == []


class TestAcceptReject:
    def test_accept_promotes_to_active(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_MODERATE, "B")
        run(db_session, uid)
        edge_id = queue(db_session, uid)[0]["edge_id"]

        accepted = accept(db_session, uid, [edge_id])
        assert accepted == 1
        assert db_session.query(KbEdge).get(edge_id).status == "active"

    def test_reject_prevents_reproposal(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_MODERATE, "B")
        run(db_session, uid)
        edge_id = queue(db_session, uid)[0]["edge_id"]

        rejected = reject(db_session, uid, [edge_id])
        assert rejected == 1
        assert db_session.query(KbEdge).get(edge_id).status == "rejected"

        # Re-run: the rejected pair must not be re-proposed.
        summary = run(db_session, uid)
        assert summary["proposed"] == 0
        assert summary["linked"] == 0

    def test_accept_is_user_scoped(self, db_session: Session, client: TestClient):
        _signup(client, uname="link-a", email="a@test.com")
        _signup(client, uname="link-b", email="b@test.com")
        uid_a = _uid(db_session, "a@test.com")
        uid_b = _uid(db_session, "b@test.com")
        _make_doc(db_session, uid_a, V_IDENTICAL, "A")
        _make_doc(db_session, uid_a, V_MODERATE, "B")
        run(db_session, uid_a)
        edge_id = queue(db_session, uid_a)[0]["edge_id"]

        accepted = accept(db_session, uid_b, [edge_id])
        assert accepted == 0
        assert db_session.query(KbEdge).get(edge_id).status == "pending"


class TestEndpoints:
    def test_force_run_and_review_flow(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, V_IDENTICAL, "A")
        _make_doc(db_session, uid, V_MODERATE, "B")

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_link", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text

        q = client.get("/api/kb/links/queue", headers={AUTH: f"Bearer {token}"})
        assert q.status_code == 200, q.text
        items = q.json()["items"]
        assert len(items) == 1
        edge_id = items[0]["edge_id"]

        acc = client.post(
            "/api/kb/links/accept",
            json={"edge_ids": [edge_id]},
            headers={AUTH: f"Bearer {token}"},
        )
        assert acc.status_code == 200, acc.text
        assert acc.json()["accepted"] == 1

        q2 = client.get("/api/kb/links/queue", headers={AUTH: f"Bearer {token}"})
        assert q2.json()["items"] == []
