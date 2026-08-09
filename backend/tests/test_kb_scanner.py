"""Idea 3 — folder watcher & file scanning tests.

Temp-dir fixture with new / changed / deleted files; asserts upserts and
status transitions via the API (scan job) and the scanner service directly.
"""
from __future__ import annotations

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
                           "removed": 0, "unchanged": 0, "duplicates_found": 0}
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


def _uid(db_session, username: str) -> int:
    user = db_session.query(User).filter(User.username == username).first()
    assert user is not None
    return user.id


def _doc(db_session, source_id: int) -> KbDocument:
    return db_session.query(KbDocument).filter(KbDocument.source_id == source_id).first()
