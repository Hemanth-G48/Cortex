"""Mood-driven session design + mood analytics.

Zenith-Study-Planner G2 (Phases 10–13). Table-driven mapping from a mood
state to a recommended study-session profile (focus length, break type,
material difficulty), plus aggregation helpers used by the mood router.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import DailyLog, JournalEntry, MoodLog

# ── Mood → session profile mapping (table-driven, per the plan) ─────────── #
# Focused → longest sessions, standard breaks, normal difficulty.
# Relaxed  → medium sessions, playful breaks, easier start.
# Stressed → shorter sessions, gentle/calming breaks, easier material.
SESSION_PARAMS: dict[str, dict] = {
    "stressed": {
        "focus_minutes": 20,
        "break_type": "Gentle (stretch / breathing / walk)",
        "difficulty": "Easy",
        "description": "Short sprints with calming breaks and lighter material to reduce pressure.",
    },
    "focused": {
        "focus_minutes": 50,
        "break_type": "Standard (5–10 min away from screen)",
        "difficulty": "Challenging",
        "description": "Long, deep focus blocks for the hardest topics while you're in the zone.",
    },
    "relaxed": {
        "focus_minutes": 35,
        "break_type": "Creative (sketch / music / mini-game)",
        "difficulty": "Normal",
        "description": "Comfortable pace with creative breaks to keep motivation up.",
    },
}


def session_params(mood: str) -> dict:
    """Return the session design profile for a mood (defaults to focused)."""
    mood = (mood or "").strip().lower()
    return SESSION_PARAMS.get(mood, SESSION_PARAMS["focused"])


# ── Analytics ───────────────────────────────────────────────────────────── #

def analytics(db: Session, user_id: int = 1, days: int = 30) -> dict:
    """Aggregate mood history: total, avg energy, dominant mood, distribution,
    and a daily trend series."""
    since = datetime.now() - timedelta(days=days)
    logs = (
        db.query(MoodLog)
        .filter(MoodLog.user_id == user_id, MoodLog.logged_at >= since)
        .order_by(MoodLog.logged_at)
        .all()
    )

    if not logs:
        return {
            "total_entries": 0,
            "avg_energy": None,
            "dominant_mood": None,
            "distribution": [{"mood": m, "count": 0} for m in ("stressed", "focused", "relaxed")],
            "daily_trend": [],
        }

    counts = Counter(log.mood for log in logs)
    distribution = [
        {"mood": m, "count": counts.get(m, 0)}
        for m in ("stressed", "focused", "relaxed")
    ]
    avg_energy = round(sum(log.energy for log in logs) / len(logs), 2)
    dominant = counts.most_common(1)[0][0]

    # Daily trend: average energy per day + most common mood that day.
    by_day: dict[date, list[MoodLog]] = {}
    for log in logs:
        by_day.setdefault(log.logged_at.date(), []).append(log)

    trend = []
    for day, day_logs in sorted(by_day.items()):
        day_counts = Counter(l.mood for l in day_logs)
        trend.append({
            "date": day.isoformat(),
            "avg_energy": round(sum(l.energy for l in day_logs) / len(day_logs), 2),
            "mood": day_counts.most_common(1)[0][0],
        })

    return {
        "total_entries": len(logs),
        "avg_energy": avg_energy,
        "dominant_mood": dominant,
        "distribution": distribution,
        "daily_trend": trend,
    }


def weekly(db: Session, user_id: int = 1, days: int = 7) -> list[dict]:
    """Return a day series ending today (zero-filled for missing days)."""
    today = date.today()
    start = today - timedelta(days=days - 1)
    logs = (
        db.query(MoodLog)
        .filter(MoodLog.user_id == user_id, MoodLog.logged_at >= datetime.combine(start, time.min))
        .all()
    )

    by_day: dict[date, list[MoodLog]] = {}
    for log in logs:
        by_day.setdefault(log.logged_at.date(), []).append(log)

    out = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        day_logs = by_day.get(day, [])
        if day_logs:
            day_counts = Counter(l.mood for l in day_logs)
            out.append({
                "date": day.isoformat(),
                "mood": day_counts.most_common(1)[0][0],
                "energy": round(sum(l.energy for l in day_logs) / len(day_logs), 2),
            })
        else:
            out.append({"date": day.isoformat(), "mood": None, "energy": None})
    return out


def insights(db: Session, user_id: int = 1, days: int = 7) -> list[dict]:
    """Pair each day's mood with a journal snippet + daily-log focus minutes."""
    today = date.today()
    start = today - timedelta(days=days - 1)

    logs = (
        db.query(MoodLog)
        .filter(MoodLog.user_id == user_id, MoodLog.logged_at >= datetime.combine(start, time.min))
        .all()
    )
    journals = {
        j.date: j for j in db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id, JournalEntry.date >= start)
        .all()
    }
    dailylogs = {
        d.date: d for d in db.query(DailyLog)
        .filter(DailyLog.user_id == user_id, DailyLog.date >= start)
        .all()
    }

    by_day: dict[date, list[MoodLog]] = {}
    for log in logs:
        by_day.setdefault(log.logged_at.date(), []).append(log)

    out = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        day_logs = by_day.get(day, [])
        journal = journals.get(day)
        daily = dailylogs.get(day)
        if day_logs:
            day_counts = Counter(l.mood for l in day_logs)
            entry = {
                "date": day.isoformat(),
                "mood": day_counts.most_common(1)[0][0],
                "energy": round(sum(l.energy for l in day_logs) / len(day_logs), 2),
            }
        else:
            entry = {"date": day.isoformat(), "mood": None, "energy": None}
        entry["journal_snippet"] = (journal.content[:160] + "…") if journal and journal.content and len(journal.content) > 160 else (journal.content if journal else None)
        entry["daily_log_focus_minutes"] = daily.time_focused if daily else None
        out.append(entry)
    return out
