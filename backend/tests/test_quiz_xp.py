"""Tests for quiz XP/gamification hooks (SyllabusAI G13, Phase 85-86)."""
from __future__ import annotations

import io

import pytest
from unittest.mock import patch

from app.services.quiz_stats import QUIZ_PASS_XP
from app.routers.materials import MATERIAL_UPLOAD_XP


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit, Material
    subject = CurriculumSubject(
        program_id=1,
        name="XP Subject",
        code="XP-SUBJ",
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
        name="XP Unit",
        description="An XP test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    # Material with enough extracted text for quiz generation (>= 50 chars).
    db.add(Material(
        unit_id=unit.id,
        title="XP Notes",
        file_type="txt",
        file_url="/uploads/xp-notes.txt",
        file_size=200,
        original_file_name="xp-notes.txt",
        extracted_text=(
            "Machine learning builds models that learn patterns from data. "
            "Supervised learning uses labeled examples while unsupervised learning "
            "discovers structure without labels."
        ),
    ))
    db.commit()
    return unit


def _make_quiz(client, unit_id, token, correct_index=0):
    mock_questions = [
        {
            "question": "Q1?",
            "options": ["A", "B", "C", "D"],
            "correct_index": correct_index,
            "explanation": "",
        },
    ]
    with patch("app.services.ai_client.generate_json", return_value={"questions": mock_questions}):
        resp = client.post(
            "/api/quizzes",
            json={"unit_id": unit_id, "num_questions": 1, "difficulty": "easy"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    return resp.json()["id"]


def _xp(client, token):
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()["user"]["total_xp"]


class TestQuizXp:
    def test_passing_quiz_grants_exact_xp(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]
        quiz_id = _make_quiz(client, unit.id, token, correct_index=0)

        initial_xp = _xp(client, token)

        # Perfect attempt (100% >= 70%) selects the correct option (index 0).
        resp = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["xp_awarded"] == QUIZ_PASS_XP
        assert _xp(client, token) == initial_xp + QUIZ_PASS_XP

    def test_failing_quiz_grants_no_xp(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]
        quiz_id = _make_quiz(client, unit.id, token, correct_index=1)

        initial_xp = _xp(client, token)

        # Wrong answer (index 0 vs correct 1) → 0% < 70% → no XP.
        resp = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["xp_awarded"] == 0
        assert _xp(client, token) == initial_xp

    def test_no_double_award_on_retry(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]
        quiz_id = _make_quiz(client, unit.id, token, correct_index=0)

        initial_xp = _xp(client, token)

        # First attempt — XP granted.
        r1 = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.json()["score"] == 1
        assert r1.json()["xp_awarded"] == QUIZ_PASS_XP
        after_first = _xp(client, token)
        assert after_first == initial_xp + QUIZ_PASS_XP

        # Second attempt (retry) — still 100%, but no double award.
        r2 = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.json()["score"] == 1
        assert r2.json()["xp_awarded"] == 0
        assert _xp(client, token) == after_first

    def test_different_quiz_grants_xp_again(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]
        quiz1 = _make_quiz(client, unit.id, token, correct_index=0)
        quiz2 = _make_quiz(client, unit.id, token, correct_index=0)

        initial_xp = _xp(client, token)
        client.post(
            f"/api/quizzes/{quiz1}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/quizzes/{quiz2}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert _xp(client, token) == initial_xp + 2 * QUIZ_PASS_XP


class TestMaterialUploadXp:
    def test_first_upload_per_unit_grants_xp(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]
        initial_xp = _xp(client, token)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("notes.txt", io.BytesIO(b"Study notes for this unit."), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert _xp(client, token) == initial_xp + MATERIAL_UPLOAD_XP

    def test_duplicate_upload_same_unit_grants_nothing(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("a.txt", io.BytesIO(b"First upload."), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        xp_after_first = _xp(client, token)

        resp = client.post(
            f"/api/curriculum/units/{unit.id}/materials",
            files={"file": ("b.txt", io.BytesIO(b"Second upload, same unit."), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert _xp(client, token) == xp_after_first
