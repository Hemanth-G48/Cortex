"""Tests for the mood tracking domain (Zenith-Study-Planner G2, Phases 8-14)."""
from __future__ import annotations

from app.models import MoodLog
from app.services import mood as mood_service


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_create_mood(client):
    resp = client.post("/api/mood", json={"mood": "focused", "energy": 4, "note": "study block"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood"] == "focused"
    assert data["energy"] == 4
    assert data["note"] == "study block"


def test_create_mood_rejects_invalid_mood(client):
    resp = client.post("/api/mood", json={"mood": "angry", "energy": 3})
    assert resp.status_code == 422


def test_create_mood_validates_energy_range(client):
    resp = client.post("/api/mood", json={"mood": "focused", "energy": 9})
    assert resp.status_code == 422


def test_list_moods(client):
    client.post("/api/mood", json={"mood": "focused", "energy": 4})
    client.post("/api/mood", json={"mood": "stressed", "energy": 2})
    resp = client.get("/api/mood")
    assert resp.status_code == 200
    moods = [m["mood"] for m in resp.json()]
    assert "focused" in moods
    assert "stressed" in moods


def test_delete_mood(client, db_session):
    resp = client.post("/api/mood", json={"mood": "relaxed", "energy": 5})
    mood_id = resp.json()["id"]
    resp = client.delete(f"/api/mood/{mood_id}")
    assert resp.status_code == 200
    assert db_session.query(MoodLog).filter(MoodLog.id == mood_id).first() is None


def test_delete_mood_missing_returns_404(client):
    resp = client.delete("/api/mood/99999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Session design mapping (Phase 10)
# ---------------------------------------------------------------------------

def test_session_params_mapping():
    stressed = mood_service.session_params("stressed")
    focused = mood_service.session_params("focused")
    relaxed = mood_service.session_params("relaxed")
    assert stressed["focus_minutes"] < focused["focus_minutes"]
    assert relaxed["focus_minutes"] < focused["focus_minutes"]
    assert stressed["difficulty"] == "Easy"
    # Unknown mood falls back to focused.
    assert mood_service.session_params("zzz")["focus_minutes"] == focused["focus_minutes"]


def test_session_params_endpoint(client):
    resp = client.get("/api/mood/session-params?mood=stressed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood"] == "stressed"
    assert data["focus_minutes"] == 20
    assert "gentle" in data["break_type"].lower()


# ---------------------------------------------------------------------------
# Analytics (Phase 11)
# ---------------------------------------------------------------------------

def _clear_moods(db_session):
    db_session.query(MoodLog).delete()
    db_session.commit()


def test_analytics_empty(client, db_session):
    _clear_moods(db_session)
    resp = client.get("/api/mood/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entries"] == 0
    assert data["dominant_mood"] is None


def test_analytics_aggregates(client, db_session):
    _clear_moods(db_session)
    client.post("/api/mood", json={"mood": "focused", "energy": 5})
    client.post("/api/mood", json={"mood": "focused", "energy": 4})
    client.post("/api/mood", json={"mood": "stressed", "energy": 2})
    resp = client.get("/api/mood/analytics")
    data = resp.json()
    assert data["total_entries"] == 3
    assert data["dominant_mood"] == "focused"
    assert data["avg_energy"] == round(11 / 3, 2)
    dist = {d["mood"]: d["count"] for d in data["distribution"]}
    assert dist["focused"] == 2
    assert dist["stressed"] == 1


# ---------------------------------------------------------------------------
# Weekly series (Phase 13)
# ---------------------------------------------------------------------------

def test_weekly_returns_seven_days(client):
    client.post("/api/mood", json={"mood": "focused", "energy": 4})
    resp = client.get("/api/mood/weekly")
    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 7
    assert days[-1]["mood"] is not None  # today's entry appears


def test_weekly_zero_fills_missing_days(client, db_session):
    _clear_moods(db_session)
    resp = client.get("/api/mood/weekly")
    days = resp.json()["days"]
    assert all(d["mood"] is None and d["energy"] is None for d in days)


# ---------------------------------------------------------------------------
# Insights (Phase 12)
# ---------------------------------------------------------------------------

def test_insights_pairs_journal_snippet(client, db_session):
    from datetime import date

    from app.models import DailyLog, JournalEntry, User

    user = db_session.query(User).first()
    today = date.today()
    # Remove any seed-created rows for today so the assertions are deterministic.
    for row in db_session.query(DailyLog).filter(DailyLog.date == today).all():
        db_session.delete(row)
    for row in db_session.query(JournalEntry).filter(JournalEntry.date == today).all():
        db_session.delete(row)
    db_session.commit()

    # Fresh journal + daily log for today so the insight pairs up.
    db_session.add(JournalEntry(
        user_id=user.id, date=today, content="Feeling good about the study plan", mood="happy",
    ))
    db_session.add(DailyLog(
        user_id=user.id, date=today, time_focused=90, status="active",
    ))
    db_session.commit()

    client.post("/api/mood", json={"mood": "focused", "energy": 4})
    resp = client.get("/api/mood/insights")
    assert resp.status_code == 200
    today_row = [r for r in resp.json() if r["date"] == today.isoformat()]
    assert today_row
    assert today_row[0]["mood"] == "focused"
    assert today_row[0]["journal_snippet"] is not None
    assert today_row[0]["daily_log_focus_minutes"] == 90


def test_mood_model_import():
    assert MoodLog.__tablename__ == "mood_logs"
