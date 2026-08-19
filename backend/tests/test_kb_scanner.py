"""Idea 3 — folder watcher & file scanning tests.

Temp-dir fixture with new / changed / deleted files; asserts upserts and
status transitions via the API (scan job) and the scanner service directly.
"""
from __future__ import annotations

import pytest

from app.models import KbDocument, User
from app.services.kb import KbService
from app.services.kb.scanner import scan_source

AUTH = "Authorization"


def _signup(client, uname="scan-user", email="scan@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Scan User",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_source(client, token, root, name="Vault"):
    resp = client.post(
        "/api/kb/sources",
        json={"name": name, "source_type": "vault_folder", "root_path": str(root)},
        headers={AUTH: f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _scan(client, token, source_id):
    resp = client.post(
        f"/api/kb/sources/{source_id}/scan", headers={AUTH: f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestWatcherLockRetry:
    """``watcher._retry_locked`` must retry a scan on a transient SQLite
    "database is locked" (the API server and watcher share one file), back
    off with rollback between attempts, and fail honestly once exhausted —
    never silently swallow a real error."""

    @staticmethod
    def _locked(exc_text: str = "database is locked"):
        from sqlalchemy.exc import OperationalError

        return OperationalError("UPDATE kb_sources SET ...", {}, Exception(exc_text))

    class _FakeDb:
        def __init__(self):
            self.rollbacks = 0

        def rollback(self):
            self.rollbacks += 1

    def test_retries_transient_lock_then_succeeds(self):
        from app.services.kb import watcher

        db = self._FakeDb()
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise self._locked()

        watcher._retry_locked(db, flaky)
        assert calls["n"] == 3  # two lock failures, one successful retry
        assert db.rollbacks == 2  # session rolled back before each retry

    def test_gives_up_honestly_when_lock_persists(self):
        from app.services.kb import watcher

        db = self._FakeDb()
        calls = {"n": 0}

        def always_locked():
            calls["n"] += 1
            raise self._locked()

        with pytest.raises(Exception, match="database is locked"):
            watcher._retry_locked(db, always_locked, attempts=3)
        assert calls["n"] == 3  # exactly the configured attempts — no infinite loop

    def test_does_not_retry_unrelated_errors(self):
        from app.services.kb import watcher

        db = self._FakeDb()
        calls = {"n": 0}

        def io_error():
            calls["n"] += 1
            raise self._locked("disk I/O error")  # locked is NOT in the message

        with pytest.raises(Exception, match="disk I/O error"):
            watcher._retry_locked(db, io_error)
        assert calls["n"] == 1  # unrelated OperationalError is not retried
        assert db.rollbacks == 0

    def test_retry_does_not_mask_non_locked_exceptions(self):
        from app.services.kb import watcher

        db = self._FakeDb()

        def boom():
            raise ValueError("real bug")

        with pytest.raises(ValueError, match="real bug"):
            watcher._retry_locked(db, boom)


class TestScanApi:
    def test_scan_discovers_and_ingests_documents(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "note.md").write_text(
            "---\ntitle: Hello\n---\n# Intro\nsome content [[link]]\n"
        )
        (tmp_path / "paper.txt").write_text("plain text")
        (tmp_path / "skip.xyz").write_text("ignored")  # not extractable
        (tmp_path / ".obsidian").mkdir()
        (tmp_path / ".obsidian" / "config.json").write_text("{}")  # noise dir

        src = _make_source(client, token, tmp_path)
        result = _scan(client, token, src["id"])

        assert result["job"]["status"] == "done"  # hermetic/sync run
        assert result["summary"]["files_seen"] == 2
        assert result["summary"]["added"] == 2

        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs["total"] == 2
        md = next(d for d in docs["items"] if d["doc_type"] == "md")
        assert md["status"] == "unchanged"
        assert md["frontmatter"]["title"] == "Hello"
        assert md["metadata"]["wikilinks"] == ["link"]
        assert md["chunk_count"] >= 1

        # Source stats recorded (phrase 26).
        src_resp = client.get(
            f"/api/kb/sources/{src['id']}", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert src_resp["files_seen"] == 2
        assert src_resp["document_count"] == 2

    def test_scan_respects_ownership(self, client, tmp_path):
        token_a = _signup(client, "scan-a", "scan-a@test.com")
        token_b = _signup(client, "scan-b", "scan-b@test.com")
        (tmp_path / "a.md").write_text("A's file")
        src = _make_source(client, token_a, tmp_path)

        # B cannot scan A's source.
        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan", headers={AUTH: f"Bearer {token_b}"}
        )
        assert resp.status_code == 404
        # B sees no documents.
        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token_b}"}).json()
        assert docs["total"] == 0

    def test_scan_subfolder_ingests_only_that_folder(self, client, tmp_path):
        """"Update from folder": scanning with ``?path=`` walks only that
        subtree — files elsewhere are not seen, not added, not swept."""
        token = _signup(client, "scan-folder", "scan-folder@test.com")
        (tmp_path / "cybersecurity" / "crypto").mkdir(parents=True)
        (tmp_path / "networks").mkdir()
        (tmp_path / "cybersecurity" / "crypto" / "hash.md").write_text("sha-256 notes")
        (tmp_path / "networks" / "tcp.md").write_text("tcp notes")
        src = _make_source(client, token, tmp_path)

        # Folder-scoped scan sees only the folder.
        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan?path=cybersecurity",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["summary"]["files_seen"] == 1
        assert body["summary"]["added"] == 1
        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs["total"] == 1
        assert docs["items"][0]["path_rel"] == "cybersecurity/crypto/hash.md"

        # A full scan then picks up the rest.
        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan", headers={AUTH: f"Bearer {token}"}
        )
        assert resp.json()["summary"]["added"] == 1

    def test_scan_subfolder_rejects_bad_paths(self, client, tmp_path):
        token = _signup(client, "scan-badpath", "scan-badpath@test.com")
        src = _make_source(client, token, tmp_path)
        for bad in ("../", "/etc", "a/../../b", "..", ""):
            qs = f"?path={bad}" if bad else ""
            resp = client.post(
                f"/api/kb/sources/{src['id']}/scan{qs}",
                headers={AUTH: f"Bearer {token}"},
            )
            if not bad:
                assert resp.status_code == 200  # blank = whole-source scan
            else:
                assert resp.status_code == 400, f"path {bad!r} should be rejected"
        # A non-existent folder inside the source → 400, not a failed job.
        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan?path=missing-folder",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400


class TestScannerService:
    def test_status_transitions(self, client, tmp_path, db_session):
        token = _signup(client)
        target = tmp_path / "a.md"
        target.write_text("version one")

        src = _make_source(client, token, tmp_path)
        source = KbService.get_source(db_session, _uid(db_session, "scan-user"), src["id"])
        assert source is not None

        summary = scan_source(db_session, source)
        assert summary == {"files_seen": 1, "added": 1, "changed": 0,
                           "moved": 0, "removed": 0, "unchanged": 0,
                           "duplicates_found": 0}
        doc = _doc(db_session, src["id"])
        assert doc.status == "new"  # scanned but not yet ingested

        # identical rescan → unchanged, no new rows
        summary = scan_source(db_session, source)
        assert summary["unchanged"] == 1 and summary["added"] == 0
        db_session.expire_all()
        assert doc.status == "new"

        # content change → changed
        old_hash = doc.content_hash
        target.write_text("version two, different content")
        summary = scan_source(db_session, source)
        assert summary["changed"] == 1
        db_session.expire_all()
        assert doc.content_hash != old_hash  # hash updated
        assert doc.status == "changed"

        # file removed → deleted
        target.unlink()
        summary = scan_source(db_session, source)
        assert summary["removed"] == 1
        db_session.expire_all()
        assert doc.status == "deleted"

    def test_scan_missing_root_returns_empty_summary(self, client, db_session):
        token = _signup(client, "scan-c", "scan-c@test.com")
        resp = client.post(
            "/api/kb/sources",
            json={"name": "Bogus", "root_path": "/definitely/not/here"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_subfolder_scan_scopes_removal_sweep(self, client, tmp_path, db_session):
        """A folder-scoped scan only marks files as deleted when they vanish
        INSIDE the scanned subtree; files elsewhere keep their status."""
        token = _signup(client, "scan-sweep", "scan-sweep@test.com")
        (tmp_path / "cybersecurity" / "net").mkdir(parents=True)
        (tmp_path / "cybersecurity" / "crypto").mkdir(parents=True)
        (tmp_path / "cybersecurity" / "net" / "a.md").write_text("net v1")
        (tmp_path / "cybersecurity" / "crypto" / "b.md").write_text("crypto v1")
        src = _make_source(client, token, tmp_path)
        source = KbService.get_source(db_session, _uid(db_session, "scan-sweep"), src["id"])

        scan_source(db_session, source)
        assert scan_source(db_session, source)["unchanged"] == 2

        # Modify a.md, delete b.md — then scan ONLY the net subfolder.
        (tmp_path / "cybersecurity" / "net" / "a.md").write_text("net v2")
        (tmp_path / "cybersecurity" / "crypto" / "b.md").unlink()

        summary = scan_source(db_session, source, subpath="cybersecurity/net")
        assert summary["changed"] == 1
        assert summary["removed"] == 0  # b.md lives outside the scanned subtree

        net_doc = (
            db_session.query(KbDocument)
            .filter(KbDocument.source_id == src["id"], KbDocument.path_rel == "cybersecurity/net/a.md")
            .first()
        )
        crypto_doc = (
            db_session.query(KbDocument)
            .filter(KbDocument.source_id == src["id"], KbDocument.path_rel == "cybersecurity/crypto/b.md")
            .first()
        )
        assert net_doc is not None and net_doc.status == "changed"
        # Untouched: still "new" (never ingested) — the folder-scoped scan did
        # not sweep it as deleted even though the file is gone from disk.
        assert crypto_doc is not None and crypto_doc.status == "new"

        # A whole-source scan now sweeps the vanished b.md.
        summary = scan_source(db_session, source)
        assert summary["removed"] == 1
        db_session.expire_all()
        assert crypto_doc.status == "deleted"

    def test_subfolder_scan_escapes_like_wildcards_in_folder_name(self, client, tmp_path, db_session):
        """A folder whose name contains LIKE wildcards (``%`` / ``_``) is
        matched literally — the sweep must not touch look-alike folders."""
        token = _signup(client, "scan-esc", "scan-esc@test.com")
        (tmp_path / "50%_Notes").mkdir(parents=True)
        (tmp_path / "50XNotes").mkdir(parents=True)  # look-alike sibling
        (tmp_path / "50%_Notes" / "a.md").write_text("escaped folder")
        (tmp_path / "50XNotes" / "b.md").write_text("sibling")
        src = _make_source(client, token, tmp_path)
        source = KbService.get_source(db_session, _uid(db_session, "scan-esc"), src["id"])

        scan_source(db_session, source)
        # Scan ONLY the wildcard-named folder, then delete its file.
        summary = scan_source(db_session, source, subpath="50%_Notes")
        assert summary["unchanged"] == 1
        (tmp_path / "50%_Notes" / "a.md").unlink()
        summary = scan_source(db_session, source, subpath="50%_Notes")
        assert summary["removed"] == 1
        # The look-alike sibling folder is untouched (not swept as deleted).
        b_doc = (
            db_session.query(KbDocument)
            .filter(KbDocument.source_id == src["id"], KbDocument.path_rel == "50XNotes/b.md")
            .first()
        )
        assert b_doc is not None and b_doc.status == "new"


def _uid(db_session, username: str) -> int:
    user = db_session.query(User).filter(User.username == username).first()
    assert user is not None
    return user.id


def _doc(db_session, source_id: int) -> KbDocument:
    return db_session.query(KbDocument).filter(KbDocument.source_id == source_id).first()
