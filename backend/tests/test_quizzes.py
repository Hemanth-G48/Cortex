"""Tests for quiz generation and attempts."""
from __future__ import annotations

import pytest
from unittest.mock import patch


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit, Material
    subject = CurriculumSubject(
        program_id=1,
        name="Quiz Subject",
        code="QUIZ-SUBJ",
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
        name="Quiz Unit",
        description="A quiz test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    # Material with enough extracted text for quiz generation (>= 50 chars).
    db.add(Material(
        unit_id=unit.id,
        title="Quiz Notes",
        file_type="txt",
        file_url="/uploads/quiz-notes.txt",
        file_size=200,
        original_file_name="quiz-notes.txt",
        extracted_text=(
            "Dynamic programming solves problems by breaking them into overlapping "
            "subproblems. It stores intermediate results to avoid recomputation. "
            "Common applications include the knapsack problem and longest common "
            "subsequence."
        ),
    ))
    db.commit()
    return unit


class TestQuizzesCreate:
    def test_create_quiz_returns_quiz(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_questions = [
            {
                "question": "What is 2+2?",
                "options": ["3", "4", "5", "6"],
                "correct_index": 1,
                "explanation": "Basic arithmetic",
            }
        ]

        with patch("app.services.ai_client.generate_json", return_value={"questions": mock_questions}):
            resp = client.post(
                "/api/quizzes",
                json={"unit_id": unit.id, "num_questions": 1, "difficulty": "easy"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["unit_id"] == unit.id
        assert data["difficulty"] == "easy"
        assert len(data["questions"]) == 1

    def test_create_quiz_uses_fallback_when_ai_fails(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        # AI returns None, fallback generates demo quiz
        with patch("app.services.ai_client.generate_json", return_value=None):
            resp = client.post(
                "/api/quizzes",
                json={"unit_id": unit.id, "num_questions": 3, "difficulty": "medium"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert len(data["questions"]) > 0