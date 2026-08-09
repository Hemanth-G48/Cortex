"""Auto-categorize tests (Phase 9, Idea 81, phrases 1-10)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CategorizeSuggestion, KbDocument, KbVersion, User
from app.services.kb.auto_categorize import (
    accept,
    category_for_document,
    queue,
    reject,
    run,
)

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "cat-user", email: str = "cat@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Categorizer",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "cat@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(
    db: Session,
    user_id: int,
    path_rel: str = "notes.md",
    category: str | None = None,
    title: str = "Note",
) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=path_rel,
        extracted_text="# Title\n\ncontent",
        frontmatter_json=json.dumps({"category": category}) if category else None,
        content_hash=f"hash-{path_rel}-{title}",
        char_count=40,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestCategorySignal:
    def test_category_from_frontmatter(self, db_session: Session):
        doc = _make_doc(db_session, 1, category="math")
        assert category_for_document(doc) == "math"

    def test_ignores_pathlike_or_missing(self, db_session: Session):
        no_signal = _make_doc(db_session, 1, title="plain")
        assert category_for_document(no_signal) is None
        pathlike = _make_doc(
            db_session, 1, title="pathlike", category="math/../etc"
        )
        assert category_for_document(pathlike) is None


class TestRun:
    def test_proposes_pending_suggestions(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid, path_rel="notes.md", category="math")
        summary = run(db_session, uid)
        assert summary["proposed"] == 1

        row = (
            db_session.query(CategorizeSuggestion)
            .filter(CategorizeSuggestion.document_id == doc.id)
            .first()
        )
        assert row is not None
        assert row.status == "pending"
        assert row.proposed_path == "math/notes.md"
        assert row.rule == "rule"

    def test_skips_already_folded(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, path_rel="math/notes.md", category="math")
        summary = run(db_session, uid)
        assert summary["proposed"] == 0
        assert summary["skipped"] == 1

    def test_never_reproposes_settled_doc(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid, path_rel="notes.md", category="math")
        run(db_session, uid)
        reject(db_session, uid, [queue(db_session, uid)[0]["id"]])
        # A second nightly run must not re-propose a settled doc.
        summary = run(db_session, uid)
        assert summary["proposed"] == 0

    def test_respects_limit(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, path_rel="a.md", category="math")
        _make_doc(db_session, uid, path_rel="b.md", category="history")
        summary = run(db_session, uid, limit=1)
        assert summary["proposed"] == 1


class TestAcceptReject:
    def test_accept_moves_and_logs_version(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid, path_rel="notes.md", category="math")
        run(db_session, uid)
        sid = queue(db_session, uid)[0]["id"]

        applied = accept(db_session, uid, [sid])
        assert applied == 1
        db_session.refresh(doc)
        assert doc.path_rel == "math/notes.md"
        assert (
            db_session.query(CategorizeSuggestion).get(sid).status == "accepted"
        )
        versions = (
            db_session.query(KbVersion)
            .filter(KbVersion.document_id == doc.id)
            .all()
        )
        assert len(versions) == 1
        assert "-> math/notes.md" in versions[0].snapshot_text

    def test_reject_keeps_path(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid, path_rel="notes.md", category="math")
        run(db_session, uid)
        sid = queue(db_session, uid)[0]["id"]

        rejected = reject(db_session, uid, [sid])
        assert rejected == 1
        db_session.refresh(doc)
        assert doc.path_rel == "notes.md"
        assert (
            db_session.query(CategorizeSuggestion).get(sid).status == "rejected"
        )

    def test_accept_is_user_scoped(self, db_session: Session, client: TestClient):
        _signup(client, uname="cat-a", email="a@test.com")
        _signup(client, uname="cat-b", email="b@test.com")
        uid_a = _uid(db_session, "a@test.com")
        uid_b = _uid(db_session, "b@test.com")
        doc = _make_doc(db_session, uid_a, path_rel="notes.md", category="math")
        run(db_session, uid_a)
        sid = queue(db_session, uid_a)[0]["id"]

        # User B cannot act on User A's proposal.
        applied = accept(db_session, uid_b, [sid])
        assert applied == 0


class TestEndpoints:
    def test_queue_and_accept_flow(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, path_rel="notes.md", category="math")

        # Trigger a run through the automation endpoint (force bypasses toggle).
        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_categorize", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text

        q = client.get(
            "/api/kb/categorize/queue", headers={AUTH: f"Bearer {token}"}
        )
        assert q.status_code == 200, q.text
        items = q.json()["items"]
        assert len(items) == 1
        sid = items[0]["id"]

        acc = client.post(
            "/api/kb/categorize/accept",
            json={"suggestion_ids": [sid]},
            headers={AUTH: f"Bearer {token}"},
        )
        assert acc.status_code == 200, acc.text
        assert acc.json()["applied"] == 1

        q2 = client.get(
            "/api/kb/categorize/queue", headers={AUTH: f"Bearer {token}"}
        )
        assert q2.json()["items"] == []
