"""Authorization tests for the materials endpoints."""
from __future__ import annotations

import io

import pytest
from fastapi import status

from app.services.security import create_bearer_token


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit

    # Fresh subject so the unique (subject_id, unit_number) constraint never
    # collides with the seeded demo catalog.
    subject = CurriculumSubject(
        program_id=1,
        name="Auth Test Subject",
        code="AUTH-SUBJ",
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
        name="Auth Test Unit",
        description="For auth testing",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


class TestMaterialUploadAuthz:
    def test_unauthenticated_post_returns_401(self, client, db_session):
        unit = _make_unit(db_session)
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
        )
        assert resp.status_code == 401

    def test_authenticated_post_allowed(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_disallowed_extension_returns_400(self, client, db_session):
        unit = _make_unit(db_session)
        token = _get_token(client)
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("script.py", io.BytesIO(b"print('hi')"), "text/x-python")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_teacher_token_can_upload(self, client, db_session):
        unit = _make_unit(db_session)
        teacher_token = create_bearer_token(1, "teacher")
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200

    def test_student_token_can_upload(self, client, db_session):
        unit = _make_unit(db_session)
        student_token = create_bearer_token(1, "student")
        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200