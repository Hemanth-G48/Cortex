"""Tests for the materials endpoints (SyllabusAI)."""
from __future__ import annotations

import io
import os

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models import CurriculumUnit, Material
from app.services.security import create_bearer_token


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


def _make_unit(db: Session) -> CurriculumUnit:
    """Create an isolated curriculum unit (own subject) directly for testing.

    Uses a fresh subject so the unique (subject_id, unit_number) constraint never
    collides with the seeded demo catalog (which owns subject 1, units 1-5).
    """
    from app.models import CurriculumSubject

    subject = CurriculumSubject(
        program_id=1,
        name="Test Subject",
        code="TEST-SUBJ",
        semester=9,
        credits=3,
        is_active=True,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    unit = CurriculumUnit(
        subject_id=subject.id,
        unit_number=1,
        name="Test Unit",
        description="A test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


class TestListUnitMaterials:
    def test_lists_materials_for_unit(self, client, db_session: Session):
        unit = _make_unit(db_session)
        token = _get_token(client)
        resp = client.get(
            f"/api/curriculum/units/{unit.id}/materials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0

    def test_search_by_title(self, client, db_session: Session):
        unit = _make_unit(db_session)
        mat = Material(
            unit_id=unit.id,
            title="Algebra Basics",
            file_type="txt",
            file_url="/uploads/test.txt",
            file_size=100,
            original_file_name="test.txt",
            extracted_text="some text",
        )
        db_session.add(mat)
        db_session.commit()

        token = _get_token(client)
        resp = client.get(
            f"/api/curriculum/units/{unit.id}/materials?q=algebra",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Algebra Basics"

    def test_search_case_insensitive(self, client, db_session: Session):
        unit = _make_unit(db_session)
        mat = Material(
            unit_id=unit.id,
            title="Algebra Basics",
            file_type="txt",
            file_url="/uploads/test.txt",
            file_size=100,
            original_file_name="test.txt",
            extracted_text="some text",
        )
        db_session.add(mat)
        db_session.commit()

        token = _get_token(client)
        resp = client.get(
            f"/api/curriculum/units/{unit.id}/materials?q=ALGEBRA",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestMaterialDetail:
    def test_detail_increments_view_count(self, client, db_session: Session):
        unit = _make_unit(db_session)
        mat = Material(
            unit_id=unit.id,
            title="Detail Test",
            file_type="txt",
            file_url="/uploads/test.txt",
            file_size=100,
            original_file_name="test.txt",
            extracted_text="some text",
        )
        db_session.add(mat)
        db_session.commit()

        token = _get_token(client)
        # First fetch
        resp = client.get(
            f"/api/materials/{mat.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["view_count"] == 1

        # Second fetch should increment again
        resp2 = client.get(
            f"/api/materials/{mat.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["view_count"] == 2

    def test_detail_404_for_missing(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.get(
            "/api/materials/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestMaterialDownload:
    def test_download_increments_count_and_returns_file(self, client, db_session: Session):
        unit = _make_unit(db_session)
        import tempfile

        tmp_dir = tempfile.mkdtemp()
        stored_name = "download_test.txt"
        file_path = os.path.join(tmp_dir, stored_name)
        content = b"downloadable content"
        with open(file_path, "wb") as f:
            f.write(content)

        mat = Material(
            unit_id=unit.id,
            title="Download Test",
            file_type="txt",
            file_url=f"/uploads/{stored_name}",
            file_size=len(content),
            original_file_name="download_test.txt",
            extracted_text="downloadable content",
        )
        db_session.add(mat)
        db_session.commit()

        # Monkeypatch the upload dir so the file is found
        from app.config import settings as app_settings

        original_dir = app_settings.UPLOAD_DIR
        app_settings.UPLOAD_DIR = tmp_dir
        try:
            token = _get_token(client)
            resp = client.get(
                f"/api/materials/{mat.id}/download",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.content == content

            # Verify download_count incremented
            db_session.refresh(mat)
            assert mat.download_count == 1
        finally:
            app_settings.UPLOAD_DIR = original_dir
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_download_404_when_file_missing(self, client, db_session: Session):
        unit = _make_unit(db_session)
        mat = Material(
            unit_id=unit.id,
            title="Missing File",
            file_type="txt",
            file_url="/uploads/nonexistent_file.txt",
            file_size=100,
            original_file_name="missing.txt",
            extracted_text="text",
        )
        db_session.add(mat)
        db_session.commit()

        token = _get_token(client)
        resp = client.get(
            f"/api/materials/{mat.id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestUploadMaterial:
    def test_authenticated_post_creates_material(self, client, db_session: Session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        file_content = b"This is a test upload for materials."
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("test_material.txt", io.BytesIO(file_content), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "test_material.txt"
        assert data["file_type"] == "txt"
        assert data["file_url"].startswith("/uploads/")
        assert data["file_size"] == len(file_content)
        assert data["original_file_name"] == "test_material.txt"
        assert data["extracted_text"] == "This is a test upload for materials."

    def test_upload_stores_file_on_disk(self, client, db_session: Session, monkeypatch):
        import tempfile

        unit = _make_unit(db_session)
        token = _get_token(client)

        tmp_dir = tempfile.mkdtemp()
        monkeypatch.setattr(
            __import__("app.config", fromlist=["settings"]).settings,
            "UPLOAD_DIR",
            tmp_dir,
        )

        file_content = b"Stored on disk test"
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("stored.txt", io.BytesIO(file_content), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        stored_name = data["file_url"].split("/")[-1]
        assert os.path.isfile(os.path.join(tmp_dir, stored_name))

        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_upload_rejects_unsupported_extension(self, client, db_session: Session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("archive.zip", io.BytesIO(b"zip data"), "application/zip")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_upload_rejects_oversized_file(self, client, db_session: Session, monkeypatch):
        from app.config import settings as app_settings

        unit = _make_unit(db_session)
        token = _get_token(client)

        original_max = app_settings.MAX_UPLOAD_MB
        app_settings.MAX_UPLOAD_MB = 1  # 1 MB cap
        try:
            oversized = b"x" * (1 * 1024 * 1024 + 1)
            resp = client.post(
                f"/api/curriculum/units/{unit.id}/materials",
                files={"file": ("huge.txt", io.BytesIO(oversized), "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 413
        finally:
            app_settings.MAX_UPLOAD_MB = original_max
