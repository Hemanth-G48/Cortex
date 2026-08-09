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
- ``get_insights`` — cache-first (``services.ai_cache``), then LLM, then a
  deterministic local fallback so the endpoint works offline.

The deterministic fallback mirrors the demo-* pattern used everywhere else in
the app (``ai_fallback``), so ``AI_ENABLED=false`` keeps the UI functional.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import Assignment, Exam, Habit, Task, User
from app.services import ai_client
from app.services.ai_cache import cached_completion

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


def get_insights(db: Session, user: User | None) -> dict:
    """Cache-first productivity insights (QuestLog's ``getProductivityInsights``)."""
    bundle = build_stats_bundle(db, user)
    prompt = insights_prompt(bundle)

    def _generate(p, **kwargs):
        return ai_client.generate(p, **kwargs)

    text, cached = cached_completion(
        prompt,
        max_tokens=500,
        temperature=0.6,
        generate=_generate,
    )
    ai_used = bool(text)
    if text is None:
        text = _fallback_insights(bundle)
    return {
        "insights": text,
        "stats": bundle,
        "cached": cached,
        "ai_used": ai_used,
    }


__all__ = ["build_stats_bundle", "insights_prompt", "get_insights"]
