"""Audit defect #20 — pre-flight validation of a candidate source root.

``GET /api/kb/sources/validate?path=`` must report whether a folder is a usable
knowledge root (exists / is a directory / readable), what a scan would index,
and whether the folder is already registered or nested inside a registered
source, so the UI can hint before ``POST /api/kb/sources`` is attempted.
"""
from __future__ import annotations

AUTH = "Authorization"


def _signup(client, uname="val-user", email="val@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Val", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _validate(client, token, path):
    return client.get(
        "/api/kb/sources/validate",
        params={"path": str(path)},
        headers={AUTH: f"Bearer {token}"},
    )


class TestValidateSourcePath:
    def test_valid_folder_reports_indexable_documents(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "note.md").write_text("# Note")
        (tmp_path / "paper.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "ignored.png").write_bytes(b"\x89PNG")

        resp = _validate(client, token, tmp_path)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["valid"] is True
        assert body["exists"] is True and body["is_dir"] is True
        assert body["readable"] is True
        # Only extractable types count (md/pdf/docx/txt) — the png is skipped.
        assert body["document_count"] == 2
        assert body["markdown_count"] == 1
        assert "note.md" in body["sample_files"]
        assert body["already_registered"] is None
        assert body["reason"] is None

    def test_missing_path_is_invalid(self, client, tmp_path):
        token = _signup(client)
        resp = _validate(client, token, tmp_path / "does-not-exist")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["valid"] is False
        assert body["exists"] is False
        assert body["reason"] == "path does not exist on disk"

    def test_file_path_is_invalid(self, client, tmp_path):
        token = _signup(client)
        target = tmp_path / "file.md"
        target.write_text("# Not a folder")
        body = _validate(client, token, target).json()
        assert body["valid"] is False
        assert body["exists"] is True and body["is_dir"] is False
        assert body["reason"] == "path is not a directory"

    def test_empty_folder_is_invalid_but_reports_zero_docs(self, client, tmp_path):
        token = _signup(client)
        body = _validate(client, token, tmp_path).json()
        assert body["valid"] is False
        assert body["document_count"] == 0
        assert "no indexable documents" in body["reason"]

    def test_registered_folder_is_flagged(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "note.md").write_text("# Note")
        created = client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token}"},
        )
        assert created.status_code == 201, created.text

        body = _validate(client, token, tmp_path).json()
        assert body["valid"] is False
        assert body["already_registered"] is not None
        assert body["already_registered"]["name"] == "Vault"
        assert body["reason"] == "folder is already registered as a source"

    def test_nested_folder_reports_parent_source(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "note.md").write_text("# Note")
        nested = tmp_path / "cybersecurity"
        nested.mkdir()
        (nested / "xss.md").write_text("# XSS")
        client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token}"},
        )

        body = _validate(client, token, nested).json()
        assert body["valid"] is True
        assert body["document_count"] == 1
        assert body["inside_source"] is not None
        assert body["inside_source"]["name"] == "Vault"

    def test_daily_life_is_excluded_from_the_document_count(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "note.md").write_text("# Note")
        daily = tmp_path / "daily-life"
        daily.mkdir()
        (daily / "2026-09-14.md").write_text("# Day")

        body = _validate(client, token, tmp_path).json()
        # daily-life is the vault's non-knowledge area — never indexed.
        assert body["document_count"] == 1
