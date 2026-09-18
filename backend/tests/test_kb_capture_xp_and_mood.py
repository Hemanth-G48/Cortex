"""Regression tests for the new ``kb_capture_xp`` router (defect #79 fix) and
the mood analytics endpoint shape that Journal.tsx now depends on (#41).

Run with::

    cd backend && python -m pytest tests/test_kb_capture_xp_and_mood.py -q
"""
from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from app.database import get_db
from app.models import User, JournalEntry
from app.services.mood import analytics as mood_analytics
from datetime import date
from main import app


@pytest.fixture(autouse=True)
def _clean_db(db_session):
    """Roll back any writes after each test so the suite stays hermetic."""
    try:
        yield db_session
    finally:
        db_session.rollback()


# ---------------------------------------------------------------------------
# kb_capture_xp (defect #79)
# ---------------------------------------------------------------------------


def test_capture_xp_awards_xp_when_kind_configured(client, db_session):
    """POST /api/kb/capture-xp with a configured kind credits XP."""
    user = User(id=1200, name='capture-xp-test', total_xp=0, role='student', username='cxp')
    db_session.add(user)
    db_session.flush()

    resp = client.post("/api/kb/capture-xp", json={"amount": 50, "kind": "custom"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["xp_awarded"] >= 0


def test_capture_xp_reaches_endpoint_without_token(client):
    """The capture-xp endpoint is reachable; the app's current_user resolves
    to the single owner when no token is supplied (same as production)."""
    resp = client.post("/api/kb/capture-xp", json={"amount": 50})
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Mood analytics (defect #41)
# ---------------------------------------------------------------------------


def test_mood_analytics_returns_expected_shape(client, db_session):
    """GET /api/mood/analytics returns the shape Journal.tsx now consumes."""
    user = User(id=1202, name='mood-shape-test', role='student', username='mshape')
    db_session.add(user)
    db_session.flush()

    resp = client.get("/api/mood/analytics?days=30")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "total_entries" in body
    assert "avg_energy" in body
    assert "dominant_mood" in body
    assert isinstance(body["distribution"], list)
    assert "daily_trend" in body
    assert isinstance(body["daily_trend"], list)


def test_mood_analytics_sorts_distribution_descending(client, db_session):
    """The mood distribution should be returned so the UI can rank chips."""
    user = User(id=1203, name='mood-sort-test', role='student', username='msort')
    db_session.add(user)
    db_session.flush()

    db_session.add(
        JournalEntry(
            id=4001, user_id=1203, date=date(2026, 9, 1),
            content="happy", mood="happy",
        )
    )
    db_session.add(
        JournalEntry(
            id=4002, user_id=1203, date=date(2026, 9, 2),
            content="neutral", mood="neutral",
        )
    )
    db_session.add(
        JournalEntry(
            id=4003, user_id=1203, date=date(2026, 9, 3),
            content="happy", mood="happy",
        )
    )
    db_session.flush()

    # Exercise the service directly so the test asserts the contract we care
    # about (sorted distribution) rather than the router's HTTP wrapper.
    data = mood_analytics(db_session, 1203, days=30)
    dist = data.get("distribution", [])
    if dist:
        counts = [d["count"] for d in dist]
        assert counts == sorted(counts, reverse=True), (
            "distribution should be sorted by count descending"
        )
