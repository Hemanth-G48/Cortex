"""Auto mind-map job tests (Phase 9, Idea 87, phrases 61-70)."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, User
from app.services.kb import KbService
from app.services.kb.auto_mindmap import MINDMAP_CACHE_KEY, run

AUTH = "Authorization"

STRUCTURED = """\
# Title

Intro paragraph.

## Section One

Body about section one.

### Subsection A

More depth.

## Section Two

Body about section two.

### Subsection B

Even more depth.
"""


def _signup(client: TestClient, uname: str = "mm-auto", email: str = "mmauto@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Mapper",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "mmauto@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_doc(db: Session, user_id: int, *, title: str = "Map", outline: list[dict] | None = None) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        path_rel=f"{title}.md",
        extracted_text=STRUCTURED,
        outline_json=KbService.json_dumps(
            outline
            or [
                {"level": 1, "text": "Section One", "char_start": 0},
                {"level": 2, "text": "Subsection A", "char_start": 0},
                {"level": 1, "text": "Section Two", "char_start": 0},
                {"level": 2, "text": "Subsection B", "char_start": 0},
            ]
        ),
        content_hash=f"hash-{title}",
        char_count=len(STRUCTURED),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestRun:
    def test_builds_and_caches_tree(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)

        summary = run(db_session, uid)
        assert summary["built"] == 1
        assert summary["cached"] == 0

        db_session.refresh(doc)
        metadata = KbService.json_loads(doc.metadata_json) or {}
        cache = metadata.get(MINDMAP_CACHE_KEY) or {}
        assert cache.get("tree") is not None
        assert cache.get("content_hash") == doc.content_hash

    def test_idempotent_rerun_is_noop(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        _make_doc(db_session, uid)

        first = run(db_session, uid)
        second = run(db_session, uid)
        assert first["built"] == 1
        assert second["cached"] == 1
        assert second["built"] == 0

    def test_skips_docs_below_min_headings(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "KB_AUTO_MINDMAP_MIN_HEADINGS", 4)
        _signup(client)
        uid = _uid(db_session)
        # Only 2 headings → not eligible.
        _make_doc(db_session, uid, title="Sparse", outline=[{"level": 1, "text": "One", "char_start": 0}])

        summary = run(db_session, uid)
        assert summary["built"] == 0

    def test_skips_non_markdown_docs(self, db_session: Session, client: TestClient):
        _signup(client)
        uid = _uid(db_session)
        doc = KbDocument(
            user_id=uid,
            title="PDF",
            doc_type="pdf",
            path_rel="PDF.pdf",
            content_hash="hash-pdf",
            char_count=10,
            outline_json=KbService.json_dumps([{"level": 1, "text": "H", "char_start": 0}] * 6),
        )
        db_session.add(doc)
        db_session.commit()

        summary = run(db_session, uid)
        assert summary["built"] == 0


class TestEndpoints:
    def test_force_run_via_automation_endpoint(self, db_session: Session, client: TestClient):
        token = _signup(client)
        uid = _uid(db_session)
        doc = _make_doc(db_session, uid)

        resp = client.post(
            "/api/kb/automation/run",
            json={"mode": "one", "name": "auto_mindmap", "force": True},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "done"

        db_session.refresh(doc)
        metadata = KbService.json_loads(doc.metadata_json) or {}
        assert MINDMAP_CACHE_KEY in metadata
