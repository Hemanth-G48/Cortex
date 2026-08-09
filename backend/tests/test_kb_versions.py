"""Idea 9 — version history & diff tests: snapshot-on-change, restore, diff,
cap enforcement, no-op on unchanged rescans.
"""
from __future__ import annotations

from app.config import settings
from app.models import KbDocument, KbVersion, User
from app.services.kb import KbService

AUTH = "Authorization"


def _signup(client, uname="ver-user", email="ver@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Versions", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _source(client, token, root):
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "source_type": "vault_folder", "root_path": str(root)},
        headers={AUTH: f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _scan(client, token, source_id):
    resp = client.post(f"/api/kb/sources/{source_id}/scan", headers={AUTH: f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _doc_id(client, token):
    docs = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
    assert docs["total"] == 1
    return docs["items"][0]["id"]


class TestVersioning:
    def test_snapshot_on_change_and_noop_on_unchanged(self, client, tmp_path):
        token = _signup(client)
        target = tmp_path / "note.md"
        target.write_text("version one content")
        src = _source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc_id = _doc_id(client, token)

        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert versions == []  # first ingest has no prior content

        target.write_text("version two content, changed!")
        _scan(client, token, src["id"])
        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert len(versions) == 1
        assert versions[0]["version_seq"] == 1
        assert "version one" in versions[0]["snapshot_text"]

        # Unchanged rescan must NOT create another version (phrase 87).
        _scan(client, token, src["id"])
        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert len(versions) == 1

    def test_diff_between_versions(self, client, tmp_path):
        token = _signup(client)
        target = tmp_path / "note.md"
        target.write_text("line one\nold line\n")
        src = _source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc_id = _doc_id(client, token)

        target.write_text("line one\nnew line\n")
        _scan(client, token, src["id"])
        target.write_text("line one\nnewer line\n")
        _scan(client, token, src["id"])

        diff = client.get(
            f"/api/kb/documents/{doc_id}/diff",
            params={"from_version": 1, "to_version": 2},
            headers={AUTH: f"Bearer {token}"},
        ).json()
        assert diff["changed"] is True
        assert "-old line" in diff["diff"]
        assert "+new line" in diff["diff"]

    def test_restore_rolls_back_and_versions_itself(self, client, tmp_path):
        token = _signup(client)
        target = tmp_path / "note.md"
        target.write_text("original text")
        src = _source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc_id = _doc_id(client, token)

        target.write_text("second revision")
        _scan(client, token, src["id"])

        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        v1 = next(v for v in versions if v["version_seq"] == 1)

        resp = client.post(
            f"/api/kb/documents/{doc_id}/restore",
            params={"version_id": v1["id"]},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["new_version_seq"] == 2  # rollback itself is versioned

        doc = client.get(
            f"/api/kb/documents/{doc_id}", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert doc["status"] == "unchanged"

        # Restored content is chunked again.
        assert doc["chunk_count"] >= 1
        # A second version now exists (the rollback snapshot).
        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert len(versions) == 2

    def test_restore_ownership(self, client, tmp_path):
        token_a = _signup(client, "ver-a", "ver-a@test.com")
        token_b = _signup(client, "ver-b", "ver-b@test.com")
        (tmp_path / "a.md").write_text("v1")
        src = _source(client, token_a, tmp_path)
        _scan(client, token_a, src["id"])
        doc_id = _doc_id(client, token_a)
        (tmp_path / "a.md").write_text("v2")
        _scan(client, token_a, src["id"])
        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token_a}"}
        ).json()

        # B cannot see A's versions.
        resp = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token_b}"}
        )
        assert resp.status_code == 404

    def test_version_cap_enforced(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "KB_MAX_VERSIONS", 3)
        token = _signup(client)
        target = tmp_path / "note.md"
        target.write_text("base")
        src = _source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc_id = _doc_id(client, token)

        for i in range(5):
            target.write_text(f"revision number {i} with distinct body content")
            _scan(client, token, src["id"])

        versions = client.get(
            f"/api/kb/documents/{doc_id}/versions", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert len(versions) == 3  # cap keeps the latest 3
        seqs = sorted(v["version_seq"] for v in versions)
        assert seqs == [3, 4, 5]

    def test_cross_user_restore_returns_404(self, client, tmp_path, db_session):
        token_a = _signup(client, "ver-c", "ver-c@test.com")
        token_b = _signup(client, "ver-d", "ver-d@test.com")
        (tmp_path / "a.md").write_text("v1")
        src = _source(client, token_a, tmp_path)
        _scan(client, token_a, src["id"])
        (tmp_path / "a.md").write_text("v2 body")
        _scan(client, token_a, src["id"])
        doc_id = _doc_id(client, token_a)
        version = db_session.query(KbVersion).first()
        resp = client.post(
            f"/api/kb/documents/{doc_id}/restore",
            params={"version_id": version.id},
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 404
