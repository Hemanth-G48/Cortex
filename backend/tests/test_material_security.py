"""Tests for material upload security guards."""
from __future__ import annotations

import io
import pytest
from fastapi import status


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit
    subject = CurriculumSubject(
        program_id=1,
        name="Security Subject",
        code="SEC-SUBJ",
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
        name="Security Unit",
        description="A security test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


class TestMaterialSecurity:
    def test_path_traversal_in_filename_rejected(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("../../etc/passwd.txt", io.BytesIO(b"content"), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_mime_extension_mismatch_rejected(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        # .txt extension but image/png content type
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("fake.txt", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_unsupported_extension_rejected(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("evil.exe", io.BytesIO(b"content"), "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_upload_size_cap_enforced(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)

        from app.config import settings
        oversized = b"x" * (settings.max_upload_bytes + 1)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("big.txt", io.BytesIO(oversized), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413