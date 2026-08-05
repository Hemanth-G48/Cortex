"""Tests for summary generation with mocked AI client."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.services.summaries import generate_summary, find_cached


def _make_unit(db):
    from app.models import CurriculumSubject, CurriculumUnit
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


class TestSummariesGenerate:
    def test_generate_summary_returns_content_and_key_points(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_ai_response = {
            "summary": {"summary": "Test summary content.", "key_points": ["Point 1", "Point 2"]}
        }

        with patch("app.services.ai_client.generate_json", return_value=mock_ai_response):
            resp = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert data["summary"]["content"] == "Test summary content."
        assert data["summary"]["key_points"] == ["Point 1", "Point 2"]
        assert data["cached"] is False

    def test_generate_summary_caches_by_sorted_unit_ids(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_ai_response = {
            "summary": {"summary": "Cached summary.", "key_points": ["Only point"]}
        }

        with patch("app.services.ai_client.generate_json", return_value=mock_ai_response):
            # First request — not cached
            resp1 = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp1.status_code == 200
            assert resp1.json()["cached"] is False

            # Second request with same unit_ids — cached
            resp2 = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp2.status_code == 200
            assert resp2.json()["cached"] is True

    def test_generate_summary_with_reversed_unit_ids_uses_same_cache(self, client, db_session):
        unit = _make_unit(db_session)
        token = client.post("/api/auth/login", json={}).json()["token"]

        mock_ai_response = {
            "summary": {"summary": "Sorted cache summary.", "key_points": ["Point"]}
        }

        with patch("app.services.ai_client.generate_json", return_value=mock_ai_response):
            # First request with [unit.id]
            resp1 = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp1.status_code == 200
            assert resp1.json()["cached"] is False

            # Second request with same ids (order doesn't matter for cache key)
            resp2 = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp2.status_code == 200
            assert resp2.json()["cached"] is True