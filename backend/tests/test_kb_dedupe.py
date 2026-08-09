"""Idea 8 — content-hash deduplication tests.

Same content + different filenames → one canonical document + a DUPLICATE_OF
edge; different content → two documents; uploads return duplicate_of_id; a file
registered in two sources still dedupes.
"""
from __future__ import annotations

from app.models import KbDocument, KbEdge

AUTH = "Authorization"


def _signup(client, uname="dup-user", email="dup@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Dup", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _source(client, token, root, name="Vault"):
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


class TestScanDedupe:
    def test_same_content_different_names_one_canonical(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "one.md").write_text("identical body")
        (tmp_path / "two.md").write_text("identical body")
        src = _source(client, token, tmp_path)

        result = _scan(client, token, src["id"])
        assert result["summary"]["duplicates_found"] == 1

        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs["total"] == 1
        # Exactly one canonical row survives — which filename is canonical
        # depends on os.walk order, not on the content.
        assert docs["items"][0]["path_rel"] in {"one.md", "two.md"}

        edge = db_session.query(KbEdge).filter(KbEdge.relation == "DUPLICATE_OF").first()
        assert edge is not None
        assert edge.weight == 1.0

    def test_different_content_two_documents(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "alpha.md").write_text("alpha content")
        (tmp_path / "beta.md").write_text("beta content")
        src = _source(client, token, tmp_path)

        result = _scan(client, token, src["id"])
        assert result["summary"]["duplicates_found"] == 0
        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs["total"] == 2
        assert db_session.query(KbEdge).filter(KbEdge.relation == "DUPLICATE_OF").count() == 0

    def test_same_file_registered_in_two_sources_dedupes(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "shared.md").write_text("shared content")
        src1 = _source(client, token, tmp_path, name="V1")
        src2 = _source(client, token, tmp_path, name="V2")

        _scan(client, token, src1["id"])
        result2 = _scan(client, token, src2["id"])
        # The same bytes from the second source are duplicates of the canonical.
        assert result2["summary"]["duplicates_found"] == 1

        docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs["total"] == 1
        edge = db_session.query(KbEdge).filter(KbEdge.relation == "DUPLICATE_OF").first()
        # One duplicate recorded when the second source was scanned.
        assert edge.weight == 1.0


class TestChangeToDuplicateContent:
    def test_changed_file_colliding_with_existing_hash_dedupes(self, client, tmp_path, db_session):
        """When a tracked file's content changes to match another document's
        content, the unique (user, hash) index must not blow up the scan — the
        colliding row is deduped away instead (reviewer-found edge case).
        """
        token = _signup(client)
        (tmp_path / "a.md").write_text("unique content alpha")
        (tmp_path / "b.md").write_text("unique content beta")
        src = _source(client, token, tmp_path)

        result = _scan(client, token, src["id"])
        assert result["job"]["status"] == "done"
        assert result["summary"]["duplicates_found"] == 0
        assert db_session.query(KbDocument).count() == 2

        # Now make b.md identical to a.md (content hash collision on change).
        (tmp_path / "b.md").write_text("unique content alpha")
        result = _scan(client, token, src["id"])
        assert result["job"]["status"] == "done"  # no IntegrityError
        assert result["summary"]["duplicates_found"] == 1

        # One canonical document survives + a DUPLICATE_OF edge.
        assert db_session.query(KbDocument).count() == 1
        edge = db_session.query(KbEdge).filter(KbEdge.relation == "DUPLICATE_OF").first()
        assert edge is not None

        # A third scan stays stable (no duplicate re-counting, no crash).
        result = _scan(client, token, src["id"])
        assert result["job"]["status"] == "done"
        assert result["summary"]["duplicates_found"] == 0
        assert db_session.query(KbDocument).count() == 1


class TestUploadDedupe:
    def test_upload_returns_duplicate_of_id(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "a.md").write_text("dup me")
        src = _source(client, token, tmp_path)
        _scan(client, token, src["id"])

        resp = client.post(
            "/api/kb/documents/upload",
            files={"file": ("copy.txt", b"dup me")},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["deduped"] is True
        assert data["duplicate_of_id"] is not None
        assert data["document"] is None

    def test_upload_new_content_creates_document(self, client, tmp_path, db_session):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            files={"file": ("fresh.txt", b"brand new text")},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["deduped"] is False
        assert data["document"]["status"] == "unchanged"  # ingested inline
        assert data["document"]["chunk_count"] >= 1
        assert db_session.query(KbDocument).count() == 1

    def test_upload_security_guards(self, client):
        token = _signup(client)
        # Bad extension
        resp = client.post(
            "/api/kb/documents/upload",
            files={"file": ("evil.exe", b"mz")},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400
        # Mime sniff mismatch (claim .md, send a PDF)
        resp = client.post(
            "/api/kb/documents/upload",
            files={"file": ("fake.md", b"%PDF-1.4 fake")},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400
