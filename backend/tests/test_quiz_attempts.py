"""Tests for quiz attempt scoring."""
from __future__ import annotations

import pytest
from unittest.mock import patch


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit, Material
    subject = CurriculumSubject(
        program_id=1,
        name="Attempt Subject",
        code="ATTEMPT-SUBJ",
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
        name="Attempt Unit",
        description="A quiz attempt test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    # Material with enough extracted text for quiz generation (>= 50 chars).
    db.add(Material(
        unit_id=unit.id,
        title="Attempt Notes",
        file_type="txt",
        file_url="/uploads/attempt-notes.txt",
        file_size=200,
        original_file_name="attempt-notes.txt",
        extracted_text=(
            "Sorting algorithms arrange data in a specific order. Common examples "
            "include quicksort, mergesort, and heapsort. Their time complexities "
            "vary and matter for large inputs."
        ),
    ))
    db.commit()
    return unit


class TestQuizAttempts:
    def test_attempt_returns_score_total_percentage_results(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_questions = [
            {
                "question": "Q1?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "Expl 1",
            },
            {
                "question": "Q2?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 2,
                "explanation": "Expl 2",
            },
        ]

        with patch("app.services.ai_client.generate_json", return_value={"questions": mock_questions}):
            resp = client.post(
                "/api/quizzes",
                json={"unit_id": unit.id, "num_questions": 2, "difficulty": "medium"},
                headers={"Authorization": f"Bearer {token}"},
            )
        quiz_id = resp.json()["id"]

        # Submit answers: Q1 correct (index 0), Q2 wrong (index 1 instead of 2)
        resp2 = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0, 1]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp2.status_code == 200
        data = resp2.json()
        assert data["score"] == 1
        assert data["total"] == 2
        assert data["percentage"] == 50.0
        assert len(data["results"]) == 2
        assert data["results"][0]["correct"] is True
        assert data["results"][1]["correct"] is False

    def test_attempt_validates_answer_bounds(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_questions = [
            {
                "question": "Q1?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "",
            },
        ]

        with patch("app.services.ai_client.generate_json", return_value={"questions": mock_questions}):
            resp = client.post(
                "/api/quizzes",
                json={"unit_id": unit.id, "num_questions": 1, "difficulty": "easy"},
                headers={"Authorization": f"Bearer {token}"},
            )
        quiz_id = resp.json()["id"]

        # Answer index out of bounds (4 is not a valid index for 4 options 0-3)
        resp2 = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [4]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp2.status_code == 200
        data = resp2.json()
        assert data["score"] == 0
        assert data["total"] == 1

    def test_attempt_invalid_answer_index_handled(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_questions = [
            {
                "question": "Q1?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "",
            },
        ]

        with patch("app.services.ai_client.generate_json", return_value={"questions": mock_questions}):
            resp = client.post(
                "/api/quizzes",
                json={"unit_id": unit.id, "num_questions": 1, "difficulty": "easy"},
                headers={"Authorization": f"Bearer {token}"},
            )
        quiz_id = resp.json()["id"]

        # None as answer (missing)
        resp2 = client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [None]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp2.status_code == 200
        data = resp2.json()
        assert data["score"] == 0