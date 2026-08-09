"""Auto-sync external repository tests (Phase 9, Idea 89, phrases 81-90)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbSource, KbVersion, User
from app.services.kb import auto_sync, utcnow
from app.services.security import decode_bearer_token

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "sync-user", email: str = "sync@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Syncer",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_source(db: Session, user_id: int, sync_type: str = "git") -> KbSource:
    source = KbSource(
        user_id=user_id,
        name="repo",
        source_type="cloud",
        root_path="/tmp/fake-repo",
        enabled=True,
        sync_type=sync_type,
        sync_cursor_json=json.dumps({}),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def _fake_git(source: KbSource, cursor: dict) -> tuple[list[dict], dict]:
    """Deterministic fake git adapter: two files, cursor advances each run."""
    if cursor.get("commit") == "abc123":
        return [], {"commit": "abc123"}  # no delta
    return (
        [
            {
                "rel_path": "notes/hello.md",
                "content": "# Hello\n\nSynced content.",
                "mtime": datetime.now(),
                "doc_type": "md",
            },
            {
                "rel_path": "notes/todo.md",
                "content": "# Todo\n\n- item one",
                "mtime": datetime.now(),
                "doc_type": "md",
            },
        ],
        {"commit": "abc123"},
    )


class TestRun:
    def test_delta_only_import(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "KB_SYNC_ENABLED", True)
        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _fake_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)

        first = auto_sync.run(db_session, uid)
        assert first["sources"] == 1
        assert first["imported"] == 2

        docs = (
            db_session.query(KbDocument)
            .filter(KbDocument.user_id == uid, KbDocument.source_id == source.id)
            .all()
        )
        assert len(docs) == 2
        # Imported through the real pipeline → chunks exist.
        chunks = db_session.query(KbChunk).filter(KbChunk.user_id == uid).count()
        assert chunks >= 2

        # Second run: cursor advanced → no deltas.
        second = auto_sync.run(db_session, uid)
        assert second["imported"] == 0

    def test_unchanged_docs_skipped(self, db_session: Session, client: TestClient, monkeypatch):
        def _always_return(src, cursor):
            # Ignores the cursor so a content-hash match path is exercised.
            return (
                [
                    {
                        "rel_path": "notes/hello.md",
                        "content": "# Hello\n\nSame content",
                        "mtime": datetime.now(),
                        "doc_type": "md",
                    }
                ],
                {"commit": "next"},
            )

        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _always_return, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)

        first = auto_sync.sync_source(db_session, source, force=True)
        assert first["imported"] == 1
        # Same content returned again → local hash already matches → skipped.
        second = auto_sync.sync_source(db_session, source, force=True)
        assert second["imported"] == 0
        assert second["unchanged"] == 1

    def test_newest_wins_conflict_preserves_local(self, db_session: Session, client: TestClient, monkeypatch):
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)

        # Local doc updated *after* the incoming change → local wins.
        doc = KbDocument(
            user_id=uid,
            source_id=source.id,
            path_rel="notes/hello.md",
            title="hello",
            doc_type="md",
            content_hash="local-hash",
            extracted_text="# Local",
            status="unchanged",
            updated_at=utcnow() + timedelta(days=1),
        )
        db_session.add(doc)
        db_session.commit()

        def _stale_git(src, cursor):
            return (
                [
                    {
                        "rel_path": "notes/hello.md",
                        "content": "# Remote older",
                        "mtime": datetime.now() - timedelta(days=2),
                        "doc_type": "md",
                    }
                ],
                {"commit": "x"},
            )

        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _stale_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        result = auto_sync.sync_source(db_session, source, force=True)
        assert result["skipped_stale"] == 1

        db_session.refresh(doc)
        assert doc.content_hash == "local-hash"  # unchanged

    def test_superseded_content_snapshotted(self, db_session: Session, client: TestClient, monkeypatch):
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)

        # Local doc with an OLDER updated_at → remote newer wins, and the old
        # content must be snapshotted into kb_versions.
        doc = KbDocument(
            user_id=uid,
            source_id=source.id,
            path_rel="notes/hello.md",
            title="hello",
            doc_type="md",
            content_hash="old-hash",
            extracted_text="# Old local",
            status="unchanged",
            updated_at=utcnow() - timedelta(days=5),
        )
        db_session.add(doc)
        db_session.commit()

        def _newer_git(src, cursor):
            return (
                [
                    {
                        "rel_path": "notes/hello.md",
                        "content": "# New remote",
                        "mtime": datetime.now(),
                        "doc_type": "md",
                    }
                ],
                {"commit": "y"},
            )

        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _newer_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        result = auto_sync.sync_source(db_session, source, force=True)
        assert result["imported"] == 1

        db_session.refresh(doc)
        assert doc.content_hash != "old-hash"
        versions = (
            db_session.query(KbVersion)
            .filter(KbVersion.document_id == doc.id)
            .all()
        )
        assert len(versions) >= 1  # superseded content preserved


class TestEndpoints:
    def test_manual_sync_endpoint(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _fake_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)

        resp = client.post(
            f"/api/kb/sources/{source.id}/sync",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["imported"] == 2

    def test_sync_status_endpoint(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "KB_SYNC_ENABLED", True)
        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _fake_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        source = _make_source(db_session, uid)
        auto_sync.run(db_session, uid)

        resp = client.get(
            f"/api/kb/sources/{source.id}/sync-status",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["sync_type"] == "git"
        assert data["cursor"].get("commit") == "abc123"

    def test_sync_disabled_toggle(self, db_session: Session, client: TestClient, monkeypatch):
        monkeypatch.setattr(settings, "KB_SYNC_ENABLED", False)
        monkeypatch.setattr(auto_sync, "ADAPTERS", {"git": _fake_git, "drive": auto_sync._drive_changes, "clip": auto_sync._clip_changes})
        token = _signup(client)
        uid = decode_bearer_token(token)["user_id"]
        _make_source(db_session, uid)

        result = auto_sync.run(db_session, uid)
        assert result["imported"] == 0  # toggle off → skipped
