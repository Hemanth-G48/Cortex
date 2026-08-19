"""AI productivity insights — QuestLog's ``getUserStats`` + ``getProductivityInsights``.

QuestLog feeds the model a *user-stats context bundle* (task completion rate,
XP, level, recent completions, community comparison) and caches the LLM
response so repeated insight requests are instant. This module adapts that to
Student Life OS's data model:

- ``build_stats_bundle`` — deterministic per-user stats (no LLM calls): task
  completion rate, XP/level/streak, recent completed tasks, upcoming
  assignments/exams, habit streaks. The analog of QuestLog's ``getUserStats``.
- ``insights_prompt`` — renders the bundle into a compact prompt that forces
  the model to reference the student's real numbers (QuestLog's prompt rules).
- ``get_insights`` — **persisted-first**: the last generated insight is stored
  per user (``AiInsight``) and reused on every later request, so opening the
  dashboard never triggers an LLM call. The LLM is only consulted when no
  snapshot exists yet (first run) or the user explicitly refreshes
  (``force=True``). ``services.ai_cache`` still short-circuits identical
  in-process re-generations, and a deterministic local fallback keeps the
  endpoint working offline.

The deterministic fallback mirrors the demo-* pattern used everywhere else in
the app (``ai_fallback``), so ``AI_ENABLED=false`` keeps the UI functional.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Assignment, Exam, Habit, Task, User
from app.services import ai_client
from app.services.ai_cache import cached_completion
from app.services.kb import KbService

# Prompt template — mirrors QuestLog's SYSTEM_PROMPT constraints (concise,
# reference actual numbers, markdown **bold** for metrics).
INSIGHTS_SYSTEM_PROMPT = (
    "You are a warm, data-driven productivity coach. Analyze the student's "
    "stats below and respond with a brief, encouraging insight (under 140 "
    "words) plus 2-3 specific, actionable suggestions. Always reference their "
    "actual numbers. Use **bold** for metrics and bullet points for suggestions."
)


def _task_stats(db: Session) -> dict:
    tasks = db.query(Task).all()
    done = [t for t in tasks if (t.status or "").lower() == "completed"]
    rate = round(len(done) / len(tasks) * 100, 1) if tasks else 0.0
    recent = sorted(done, key=lambda t: t.due_date or date.min, reverse=True)[:5]
    return {
        "total": len(tasks),
        "completed": len(done),
        "completion_rate": rate,
        "recent_completions": [
            {"title": t.title, "subject": t.subject_tag, "due_date": str(t.due_date) if t.due_date else None}
            for t in recent
        ],
    }


def _assignment_stats(db: Session) -> dict:
    rows = db.query(Assignment).filter(Assignment.due_date.is_not(None)).all()
    today = date.today()
    pending = [a for a in rows if (a.status or "").lower() != "completed"]
    upcoming = sorted((a for a in pending if a.due_date >= today), key=lambda a: a.due_date)[:5]
    return {
        "pending": len(pending),
        "upcoming": [
            {"title": a.title, "due_date": str(a.due_date), "status": a.status}
            for a in upcoming
        ],
    }


def _exam_stats(db: Session) -> dict:
    rows = db.query(Exam).filter(Exam.date.is_not(None)).all()
    today = date.today()
    upcoming = sorted((e for e in rows if e.date >= today), key=lambda e: e.date)[:5]
    return {
        "upcoming_exams": [
            {"title": e.title, "date": str(e.date)} for e in upcoming
        ],
    }


def _habit_stats(db: Session) -> dict:
    habits = db.query(Habit).filter(Habit.is_archived.is_(False)).all()
    active = [h for h in habits if (h.current_streak or 0) > 0]
    return {
        "total": len(habits),
        "active_streaks": len(active),
        "best_streak": max((h.current_streak or 0) for h in habits) if habits else 0,
    }


def build_stats_bundle(db: Session, user: User | None) -> dict:
    """Deterministic per-user stats bundle (QuestLog's ``getUserStats``)."""
    return {
        "user": {
            "level": user.current_level if user else None,
            "total_xp": user.total_xp if user else 0,
            "streak": user.current_streak if user else 0,
        },
        "tasks": _task_stats(db),
        "assignments": _assignment_stats(db),
        "exams": _exam_stats(db),
        "habits": _habit_stats(db),
    }


def insights_prompt(bundle: dict) -> str:
    """Render the stats bundle into the insight prompt (QuestLog pattern)."""
    u = bundle["user"]
    t = bundle["tasks"]
    a = bundle["assignments"]
    e = bundle["exams"]
    h = bundle["habits"]

    recent_lines = "\n".join(
        f"- \"{c['title']}\""
        + (f" ({c['subject']})" if c.get("subject") else "")
        + (f" due {c['due_date']}" if c.get("due_date") else "")
        for c in t["recent_completions"]
    ) or "- none yet"

    upcoming_lines = "\n".join(
        f"- \"{x['title']}\" due {x['due_date']} ({x['status']})"
        for x in a["upcoming"]
    ) or "- none"

    exam_lines = "\n".join(f"- \"{x['title']}\" on {x['date']}" for x in e["upcoming_exams"]) or "- none"

    return (
        f"Student stats:\n"
        f"- Level {u['level']}, {u['total_xp']} XP, {u['streak']}-day streak\n"
        f"- Task completion rate: {t['completion_rate']}% ({t['completed']}/{t['total']})\n"
        f"- Pending assignments: {a['pending']}\n"
        f"- Habit streaks: {h['active_streaks']} active, best {h['best_streak']} days\n\n"
        f"Recently completed:\n{recent_lines}\n\n"
        f"Upcoming assignments:\n{upcoming_lines}\n\n"
        f"Upcoming exams:\n{exam_lines}\n\n"
        "Provide a brief encouraging analysis of their productivity patterns "
        "and 2-3 specific suggestions for improvement."
    )


def _fallback_insights(bundle: dict) -> str:
    """Deterministic local insights when AI is disabled/unreachable."""
    u = bundle["user"]
    t = bundle["tasks"]
    a = bundle["assignments"]
    h = bundle["habits"]

    lines = [f"**{t['completion_rate']}%** of your tasks are complete ({t['completed']}/{t['total']})."]
    if a["pending"]:
        lines.append(f"You have **{a['pending']}** pending assignments — start with the earliest due date.")
    if h["active_streaks"]:
        lines.append(f"You're keeping **{h['active_streaks']}** habit streaks alive (best: **{h['best_streak']}** days). Keep the chain going!")
    else:
        lines.append("No active habit streaks yet — a small daily habit is a great way to build momentum.")
    lines.append(f"Total XP: **{u['total_xp']}** at level **{u['level']}**.")
    lines.append("Suggestions: 1) knock out one high-priority task today, 2) review upcoming deadlines, 3) keep one habit streak alive.")
    return "\n".join(lines)


def load_saved_insight(db: Session, user_id: int) -> dict | None:
    """Return the persisted insight snapshot for a user, or None.

    ``cached=True`` + ``analyzed_at`` let the UI show a "reused, not
    recomputed" badge next to the last-updated timestamp.
    """
    from app.models import AiInsight

    row = (
        db.query(AiInsight)
        .filter(AiInsight.user_id == user_id)
        .first()
    )
    if row is None:
        return None
    # SQLite stores DateTime without tzinfo — re-attach UTC so the timestamp
    # matches fresh computes exactly (``+00:00`` suffix), mirroring the gap
    # analysis cache (``load_saved_goal_gaps``).
    analyzed = row.analyzed_at
    if analyzed is not None and analyzed.tzinfo is None:
        analyzed = analyzed.replace(tzinfo=timezone.utc)
    return {
        "insights": row.text,
        "stats": KbService.json_loads(row.stats_json) or {},
        "cached": True,
        "ai_used": bool(row.ai_used),
        "analyzed_at": analyzed.isoformat() if analyzed else None,
    }


def _save_insight(
    db: Session,
    user_id: int,
    text: str,
    bundle: dict,
    ai_used: bool,
) -> dict:
    """Upsert the snapshot (one row per user) and return the response payload."""
    from app.models import AiInsight

    now = datetime.now(timezone.utc)
    row = (
        db.query(AiInsight)
        .filter(AiInsight.user_id == user_id)
        .first()
    )
    if row is None:
        row = AiInsight(user_id=user_id, text=text, ai_used=ai_used, analyzed_at=now)
        db.add(row)
    else:
        row.text = text
        row.ai_used = ai_used
        row.analyzed_at = now
    row.stats_json = KbService.json_dumps(bundle)
    try:
        db.flush()
    except IntegrityError:
        # Rare race (two first-loads at once): the unique user row already
        # exists — roll back the insert and update it instead.
        db.rollback()
        row = (
            db.query(AiInsight)
            .filter(AiInsight.user_id == user_id)
            .first()
        )
        if row is None:
            raise
        row.text = text
        row.ai_used = ai_used
        row.stats_json = KbService.json_dumps(bundle)
        row.analyzed_at = now
        db.flush()
    return {
        "insights": text,
        "stats": bundle,
        "cached": False,
        "ai_used": ai_used,
        "analyzed_at": now.isoformat(),
    }


def get_insights(db: Session, user: User | None, *, force: bool = False) -> dict:
    """Persisted-first productivity insights — no LLM on page loads.

    A saved snapshot is returned immediately (``cached=True``). Only the
    explicit ``force`` refresh (or the very first request) consults the
    provider — mirroring the save-and-reuse pattern used by gap analysis and
    summaries so opening the dashboard never spends a model call.
    """
    user_id = user.id if user else 0
    saved = load_saved_insight(db, user_id) if not force else None
    if saved is not None:
        return saved

    bundle = build_stats_bundle(db, user)
    prompt = insights_prompt(bundle)

    if force:
        # Explicit user refresh: bypass the in-memory TTL cache so the model
        # is genuinely called on request (never served a cached copy).
        text = ai_client.generate(prompt, max_tokens=500, temperature=0.6)
    else:
        text, _cached = cached_completion(
            prompt,
            max_tokens=500,
            temperature=0.6,
            generate=lambda p, **kwargs: ai_client.generate(p, **kwargs),
        )
    ai_used = bool(text)
    if text is None:
        text = _fallback_insights(bundle)
        ai_used = False
    return _save_insight(db, user_id, text, bundle, ai_used)


__all__ = ["build_stats_bundle", "insights_prompt", "get_insights"]
