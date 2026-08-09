"""Scheduled auto-tag job tests (Phase 9, Idea 82, phrases 11-20)."""
from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbDocumentTag, KbTag, User
from app.services.kb.auto_tag import run

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "tag-job", email: str = "tagjob@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Tagger",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "tagjob@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(
    db: Session,
    user_id: int,
    *,
    title: str = "Doc",
    tags_dirty: bool = True,
    frontmatter_tags: list[str] | None = None,
    content: str = "# Title\n\nplain text here",
) -> KbDocument:
    fm = json.dumps({"tags": frontmatter_tags}) if frontmatter_tags else None
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=f"{title}.md",
        extracted_text=content,
        frontmatter_json=fm,
        content_hash=f"hash-{title}",
        char_count=len(content),
        tags_dirty=tags_dirty,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _add_chunk(db: Session, doc: KbDocument, content: str) -> None:
    db.add(
        KbChunk(
            user_id=doc.user_id,
            document_id=doc.id,
            seq=0,
            content=content,
            token_estimate=max(1, len(content) // 4),
        )
    )
    db.commit()


class TestScheduledRun:
    def test_seeds_rule_tags_and_clears_dirty(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid, title="notes", frontmatter_tags=["python"])

        summary = run(db_session, uid)
        assert summary["processed"] == 1
        assert summary["tags_added"] >= 1

        db_session.refresh(doc)
        assert doc.tags_dirty is False
        tag_names = {
            row.name
            for row in (
                db_session.query(KbTag)
                .join(KbDocumentTag, KbTag.id == KbDocumentTag.tag_id)
                .filter(KbDocumentTag.document_id == doc.id)
                .all()
            )
        }
        assert "python" in tag_names

    def test_skips_clean_docs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="clean", tags_dirty=False)
        summary = run(db_session, uid)
        assert summary["processed"] == 0

    def test_respects_limit(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="a")
        _make_doc(db_session, uid, title="b")
        _make_doc(db_session, uid, title="c")
        summary = run(db_session, uid, limit=2)
        assert summary["processed"] == 2

    def test_deterministic_fallback_when_ai_disabled(
        self, db_session: Session, client: TestClient, monkeypatch
    ):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(
            db_session,
            uid,
            title="ml",
            content=(
                "# Machine Learning\n\nNeural networks for deep learning. "
                "Deep learning is a subset of machine learning. "
                "Training requires large datasets."
            ),
        )
        _add_chunk(db_session, doc, doc.extracted_text)

        monkeypatch.setattr(settings, "AI_ENABLED", False)
        summary = run(db_session, uid)
        assert summary["processed"] == 1

        ai_rows = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.provenance == "ai",
            )
            .all()
        )
        # TF-IDF fallback must persist at least one AI proposal.
        assert len(ai_rows) >= 1

    def test_user_isolation(self, db_session: Session, client: TestClient):
        _signup(client, uname="tag-a", email="a@test.com")
        _signup(client, uname="tag-b", email="b@test.com")
        uid_a = _uid(db_session, "a@test.com")
        uid_b = _uid(db_session, "b@test.com")
        _make_doc(db_session, uid_a, title="only-a")
        _make_doc(db_session, uid_b, title="only-b")

        summary = run(db_session, uid_a)
        assert summary["processed"] == 1
        remaining = (
            db_session.query(KbDocument)
            .filter(KbDocument.user_id == uid_b, KbDocument.tags_dirty == True)  # noqa: E712
            .count()
        )
        assert remaining == 1


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="notes", frontmatter_tags=["django"])

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_tag", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_tag"
        assert resp.json()["status"] == "done"

        dirty = (
            db_session.query(KbDocument)
            .filter(KbDocument.user_id == uid, KbDocument.tags_dirty == True)  # noqa: E712
            .count()
        )
        assert dirty == 0
