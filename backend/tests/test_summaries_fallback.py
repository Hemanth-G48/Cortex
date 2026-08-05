"""Tests for summary generation fallback when AI is disabled."""
from __future__ import annotations

import pytest
from unittest.mock import patch


def test_summary_fallback_when_ai_disabled(client, db_session):
    """When AI returns None (disabled), summaries use deterministic fallback."""
    from app.models import CurriculumSubject, CurriculumUnit

    subject = CurriculumSubject(
        program_id=1,
        name="Fallback Subject",
        code="FALLBACK-SUBJ",
        semester=9,
        credits=3,
        is_active=True,
    )
    db_session.add(subject)
    db_session.commit()
    db_session.refresh(subject)

    unit = CurriculumUnit(
        subject_id=subject.id,
        unit_number=1,
        name="Fallback Unit",
        description="A fallback test unit",
    )
    db_session.add(unit)
    db_session.commit()
    db_session.refresh(unit)

    token = client.post("/api/auth/login", json={}).json()["token"]

    # Monkeypatch generate_json to return None (AI disabled/unreachable)
    with patch("app.services.ai_client.generate_json", return_value=None):
        resp = client.post(
            "/api/summaries",
            json={"unit_ids": [unit.id]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    # Fallback returns deterministic content
    assert data["cached"] is False
    assert isinstance(data["summary"]["content"], str)
    assert isinstance(data["summary"]["key_points"], list)