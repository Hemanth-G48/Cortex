"""Tests for quiz analytics/stats."""
from __future__ import annotations

import pytest
from unittest.mock import patch


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit, Material
    subject = CurriculumSubject(
        program_id=1,
        name="Stats Subject",
        code="STATS-SUBJ",
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
        name="Stats Unit",
        description="A stats test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    # Material with enough extracted text for quiz generation (>= 50 chars).
    db.add(Material(
        unit_id=unit.id,
        title="Stats Notes",
        file_type="txt",
        file_url="/uploads/stats-notes.txt",
        file_size=200,
        original_file_name="stats-notes.txt",
        extracted_text=(
            "Data structures organize information for efficient access. Arrays, "
            "linked lists, stacks, queues, trees, and graphs each trade off "
            "different performance characteristics."
        ),
    ))
    db.commit()
    return unit


class TestQuizStats:
    def test_analytics_returns_aggregate_stats(self, client, db_session):
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

        # Submit a perfect attempt
        client.post(
            f"/api/quizzes/{quiz_id}/attempt",
            json={"answers": [0]},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Get analytics
        resp2 = client.get(
            "/api/quizzes/analytics",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp2.status_code == 200
        data = resp2.json()
        assert "avg_score" in data
        assert "best_score" in data
        assert "total_attempts" in data
        assert data["total_attempts"] >= 1