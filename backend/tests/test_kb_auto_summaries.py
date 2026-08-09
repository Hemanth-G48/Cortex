"""Auto-summary job tests (Phase 9, Idea 86, phrases 51-60)."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbSummary, User
from app.services.kb.auto_summary import run

AUTH = "Authorization"


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Auto summary tests use the deterministic heading-based fallback."""
    monkeypatch.setattr(settings, "AI_ENABLED", False)


def _signup(client: TestClient, uname: str = "sum-auto", email: str = "sumauto@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Summarizer",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "sumauto@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(
    db: Session,
    user_id: int,
    *,
    title: str = "Doc",
    summary_dirty: bool = True,
    status: str = "changed",
) -> KbDocument:
    content = f"# {title}\n\nFirst section about {title}.\n\nSecond section with details."
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=f"{title}.md",
        extracted_text=content,
        content_hash=f"hash-{title}",
        char_count=len(content),
        summary_dirty=summary_dirty,
        status=status,
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


class TestRun:
    def test_summarizes_dirty_docs_and_clears_flag(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)

        summary = run(db_session, uid)
        assert summary["processed"] == 1
        assert summary["summarized"] == 1

        db_session.refresh(doc)
        assert doc.summary_dirty is False
        row = (
            db_session.query(KbSummary)
            .filter(KbSummary.document_id == doc.id)
            .first()
        )
        assert row is not None
        assert row.content  # deterministic fallback produced a summary

    def test_skips_clean_docs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="Clean", summary_dirty=False)

        summary = run(db_session, uid)
        assert summary["processed"] == 0

    def test_changed_docs_prioritized(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid, title="Unchanged", status="unchanged")
        _make_doc(db_session, uid, title="Changed", status="changed")

        summary = run(db_session, uid, limit=1)
        assert summary["processed"] == 1
        # The changed doc wins the priority slot.
        row = (
            db_session.query(KbSummary)
            .join(KbDocument, KbDocument.id == KbSummary.document_id)
            .filter(KbDocument.title == "Changed")
            .first()
        )
        assert row is not None

    def test_respects_per_night_cap(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        for t in ("A", "B", "C"):
            _make_doc(db_session, uid, title=t)

        summary = run(db_session, uid, limit=2)
        assert summary["processed"] == 2

    def test_deterministic_fallback_when_ai_disabled(self, db_session: Session, client: TestClient, monkeypatch):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)
        monkeypatch.setattr(settings, "AI_ENABLED", False)

        summary = run(db_session, uid)
        assert summary["summarized"] == 1
        row = (
            db_session.query(KbSummary)
            .filter(KbSummary.document_id == doc.id)
            .first()
        )
        assert row is not None
        assert row.content


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid)

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_summary", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["job"] == "auto_summary"
        assert resp.json()["status"] == "done"

        dirty = (
            db_session.query(KbDocument)
            .filter(KbDocument.user_id == uid, KbDocument.summary_dirty == True)  # noqa: E712
            .count()
        )
        assert dirty == 0
