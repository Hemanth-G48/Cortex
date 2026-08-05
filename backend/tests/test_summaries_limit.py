"""Tests for the summary daily generation guard (SyllabusAI G13, Phase 87)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings


def _make_unit(db, idx: int):
    from app.models import CurriculumSubject, CurriculumUnit, Material
    subject = CurriculumSubject(
        program_id=1,
        name=f"Limit Subject {idx}",
        code=f"LIMIT-SUBJ-{idx}",
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
        name=f"Limit Unit {idx}",
        description="A limit-guard test unit",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    db.add(Material(
        unit_id=unit.id,
        title=f"Notes {idx}",
        file_type="txt",
        file_url=f"/uploads/limit-{idx}.txt",
        file_size=200,
        original_file_name=f"limit-{idx}.txt",
        extracted_text=(
            "Enough material text to generate a summary. "
            "This sentence provides content for the AI pipeline."
        ),
    ))
    db.commit()
    return unit


def _token(client):
    return client.post("/api/auth/login", json={}).json()["token"]


class TestSummaryDailyLimit:
    def test_returns_429_after_daily_cap(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SUMMARY_DAILY_LIMIT", 3)
        token = _token(client)
        mock_ai = {"summary": {"summary": "S", "key_points": ["K"]}}

        for i in range(3):
            unit = _make_unit(db_session, i)
            with patch("app.services.ai_client.generate_json", return_value=mock_ai):
                resp = client.post(
                    "/api/summaries",
                    json={"unit_ids": [unit.id]},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()["cached"] is False

        # Fourth new generation exceeds the cap.
        unit4 = _make_unit(db_session, 99)
        with patch("app.services.ai_client.generate_json", return_value=mock_ai):
            resp = client.post(
                "/api/summaries",
                json={"unit_ids": [unit4.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 429
        assert "limit" in resp.json()["detail"].lower()

    def test_cached_lookup_exempt_from_cap(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SUMMARY_DAILY_LIMIT", 1)
        token = _token(client)
        unit = _make_unit(db_session, 0)
        mock_ai = {"summary": {"summary": "S", "key_points": ["K"]}}

        with patch("app.services.ai_client.generate_json", return_value=mock_ai):
            resp = client.post(
                "/api/summaries",
                json={"unit_ids": [unit.id]},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

        # Cache hit should still work even at the cap.
        resp2 = client.post(
            "/api/summaries",
            json={"unit_ids": [unit.id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["cached"] is True

    def test_demo_fallback_exempt_from_cap(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "SUMMARY_DAILY_LIMIT", 1)
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _token(client)
        mock_ai = {"summary": {"summary": "S", "key_points": ["K"]}}

        for i in range(3):
            unit = _make_unit(db_session, i)
            with patch("app.services.ai_client.generate_json", return_value=mock_ai):
                resp = client.post(
                    "/api/summaries",
                    json={"unit_ids": [unit.id]},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 200, resp.text
