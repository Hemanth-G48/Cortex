"""Idea 98 — goal planning & reflection system.

- **Goal↔roadmap linkage** (phrase 71): goals gain ``subject_id``/``roadmap_id``
  via the ``goals`` table; progress is tracked from roadmap topic completion.
- **Term-goal derivation** (phrase 72): "master DSA" goals auto-proposed from
  active subjects (reviewable, deterministic — no LLM cost).
- **Weekly reflection** (phrases 73–75): one ``Reflection`` row per
  ``(user_id, week_start)`` generated from that week's ``learning_events``
  (budget-capped LLM; deterministic fallback from event aggregates).
- **Insight push** (phrase 76): a coalesced ``Notification`` per week.
- **Plan adjustments** (phrase 77): reuse the Phase 8 Idea 80 ``adapt_roadmap``
  machinery when insights flag a change.

All deterministic when AI is disabled.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Goal,
    LearningEvent,
    Notification,
    Reflection,
    SubjectProfile,
    Topic,
)
from app.services import ai_client
from app.services.kb import KbService, utcnow
from app.services.kb import ai_log as ai_log_service
from app.services.kb.adapt import adapt_roadmap
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.mastery import mastery_by_topic

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Week helpers
# --------------------------------------------------------------------------- #


def week_start(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def _week_events(db: Session, user_id: int, ws: date) -> list[LearningEvent]:
    since = datetime.combine(ws, datetime.min.time())
    until = since + timedelta(days=7)
    return (
        db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.created_at >= since,
            LearningEvent.created_at < until,
        )
        .order_by(LearningEvent.created_at.asc())
        .all()
    )


# --------------------------------------------------------------------------- #
# Reflection generation (phrase 75)
# --------------------------------------------------------------------------- #


def get_or_generate(
    db: Session, user_id: int, ws: date | None = None, *, regenerate: bool = False
) -> dict:
    """Return the weekly reflection, generating on miss (phrase 75)."""
    ws = week_start(ws)
    row = (
        db.query(Reflection)
        .filter(Reflection.user_id == user_id, Reflection.week_start == ws)
        .first()
    )
    if row is not None and not regenerate:
        return {**_row_dict(row), "pushed": False}

    events = _week_events(db, user_id, ws)
    insights = _generate_insights(db, user_id, events)
    content = _compose_content(insights, events)
    pushed = False

    if row is None:
        row = Reflection(user_id=user_id, week_start=ws)
        db.add(row)
    row.content = content
    row.insights = KbService.json_dumps(insights)
    db.flush()

    # Coalesced notification (phrase 76) — one per user+week.
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.kind == "reflection",
            Notification.ref_type == f"week:{ws.isoformat()}",
        )
        .first()
    )
    if existing is None:
        db.add(
            Notification(
                user_id=user_id,
                kind="reflection",
                title=f"Weekly reflection — {ws.isoformat()}",
                body=_notification_body(insights),
                ref_type=f"week:{ws.isoformat()}",
            )
        )
        pushed = True

    ai_log_service.log_event(
        db, user_id,
        feature="reflection",
        request=f"weekly reflection {ws.isoformat()}",
        response=content[:1000],
    )
    db.flush()
    return {**_row_dict(row), "pushed": pushed}


def _generate_insights(db: Session, user_id: int, events: list[LearningEvent]) -> dict:
    """Budget-capped LLM insight extraction; deterministic fallback."""
    if events and ai_client.ai_available() and budget_allows(db, user_id):
        parsed = ai_client.generate_json(_insight_prompt(events), max_tokens=800, temperature=0.5)
        insights = _normalise_insights(parsed)
        if insights:
            record_generation(db, user_id, "summary")
            return insights
    return _fallback_insights(events)


def _insight_prompt(events: list[LearningEvent]) -> str:
    lines = "\n".join(
        f"- [{e.created_at.date().isoformat() if e.created_at else '?'}] {e.event_type} "
        f"value={e.value}"
        for e in events[-50:]
    )
    return (
        "Analyze this week of learning events. Return ONLY JSON: "
        '{"worked": ["..."], "struggled": ["..."], "change": ["..."], '
        '"insights": ["..."]}. Max 4 each.\nEVENTS:\n' + lines
    )


def _normalise_insights(parsed: object) -> dict:
    if not isinstance(parsed, dict):
        return {}
    out: dict = {}
    for key in ("worked", "struggled", "change", "insights"):
        val = parsed.get(key)
        out[key] = [str(x).strip()[:300] for x in val if str(x).strip()] if isinstance(val, list) else []
    if not any(out.values()):
        return {}
    return out


def _fallback_insights(events: list[LearningEvent]) -> dict:
    """Deterministic fallback from event aggregates (phrase 75)."""
    by_type: dict[str, int] = {}
    total_minutes = 0.0
    accuracies: list[float] = []
    for e in events:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        if e.event_type in ("session", "study"):
            total_minutes += float(e.value or 0.0)
        if e.event_type in ("quiz", "revision"):
            accuracies.append(max(0.0, min(1.0, float(e.value or 0.0))))
    worked: list[str] = []
    struggled: list[str] = []
    change: list[str] = []
    insights: list[str] = []
    if not events:
        worked = ["No study activity recorded this week."]
        insights = ["Plan a minimum weekly study target to build momentum."]
    else:
        active = sum(v for k, v in by_type.items() if k != "outcome")
        worked.append(f"{active} learning sessions logged ({len(events)} events total).")
        if accuracies:
            avg = sum(accuracies) / len(accuracies)
            worked.append(f"Average quiz/revision accuracy {avg:.0%}.")
            if avg < 0.6:
                struggled.append("Accuracy below 60% — revisit weak topics.")
                change.append("Front-load revision on the lowest-scoring topics.")
        if total_minutes < 120:
            change.append("Study volume was under 2 hours — raise the weekly target.")
        insights.append("Consistency beats cramming: spread sessions across days.")
    return {"worked": worked, "struggled": struggled, "change": change, "insights": insights}


def _compose_content(insights: dict, events: list[LearningEvent]) -> str:
    lines = ["# Weekly Reflection"]
    lines.append("## Worked")
    lines.extend(f"- {x}" for x in (insights.get("worked") or []))
    lines.append("## Struggled")
    lines.extend(f"- {x}" for x in (insights.get("struggled") or []))
    lines.append("## What to change")
    lines.extend(f"- {x}" for x in (insights.get("change") or []))
    lines.append("## Insights")
    lines.extend(f"- {x}" for x in (insights.get("insights") or []))
    return "\n".join(lines)


def _notification_body(insights: dict) -> str:
    change = insights.get("change") or []
    return "\n".join(change[:3]) if change else "Your weekly reflection is ready."


def _row_dict(row: Reflection) -> dict:
    return {
        "id": row.id,
        "week_start": row.week_start.isoformat(),
        "content": row.content,
        "insights": KbService.json_loads(row.insights) or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_reflections(db: Session, user_id: int, limit: int = 12) -> list[dict]:
    rows = (
        db.query(Reflection)
        .filter(Reflection.user_id == user_id)
        .order_by(Reflection.week_start.desc())
        .limit(limit)
        .all()
    )
    return [_row_dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Plan adjustments (phrase 77)
# --------------------------------------------------------------------------- #


def apply_plan_adjustments(db: Session, user_id: int, insights: dict | None = None) -> list[dict]:
    """Run the Phase 8 adapt machinery per subject when insights flag a change.

    ``insights`` may come from a fresh reflection; when absent the adjustment
    is driven by the observable adapt triggers (``adapt.should_adapt``).
    """
    insights = insights or {}
    change_flags = " ".join(insights.get("change") or []).lower()
    if change_flags and not any(k in change_flags for k in ("weak", "revis", "master", "plan", "front-load")):
        return []
    subject_ids = {
        t.subject_id
        for t in db.query(Topic).filter(Topic.user_id == user_id).all()
        if t.subject_id
    }
    from app.services.kb import adapt as adapt_service

    applied: list[dict] = []
    for sid in sorted(subject_ids):
        # Adapt only when the observable triggers warrant it (never churn).
        triggers = [
            r for r in adapt_service.should_adapt(db, user_id, sid)
            if "no material change" not in r
        ]
        if not triggers:
            continue
        result = adapt_service.adapt_roadmap(db, user_id, sid)
        db.commit()
        if result.get("diff", {}).get("reason") != "no material change":
            applied.append({"subject_id": sid, "adaptation": result})
    return applied


# --------------------------------------------------------------------------- #
# Goals ↔ roadmaps (phrases 71–72)
# --------------------------------------------------------------------------- #


def derive_goals(db: Session, user_id: int, quarter: str | None = None, year: int | None = None) -> list[dict]:
    """Auto-propose "master {subject}" goals from active subjects (phrase 72).

    Deterministic and reviewable: proposals are NOT persisted automatically —
    the caller confirms via ``confirm_derived_goal``. Never overwrites existing
    goals for the same subject.
    """
    today = date.today()
    q = quarter or f"Q{(today.month - 1) // 3 + 1}"
    y = year or today.year
    profiles = (
        db.query(SubjectProfile)
        .filter(SubjectProfile.user_id == user_id, SubjectProfile.status == "confirmed")
        .all()
    )
    existing_subjects = {
        g.subject_id
        for g in db.query(Goal).filter(Goal.user_id == user_id, Goal.subject_id.is_not(None)).all()
    }
    proposals = []
    for profile in profiles:
        sid = profile.curriculum_subject_id
        if sid is None or sid in existing_subjects:
            continue
        name = profile.parsed_title or f"subject {sid}"
        proposals.append(
            {
                "subject_id": sid,
                "title": f"Master {name}",
                "quarter": q,
                "year": y,
                "target_date": _end_of_quarter(q, y).isoformat(),
            }
        )
    return proposals


def _end_of_quarter(q: str, year: int) -> date:
    month = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}.get(q, 12)
    return date(year, month, 28)


def confirm_derived_goal(db: Session, user_id: int, proposal: dict) -> Goal:
    """Persist a derived-goal proposal (reviewable, phrase 72)."""
    title = (proposal.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    goal = Goal(
        user_id=user_id,
        title=title[:200],
        quarter=str(proposal.get("quarter") or "Q1")[:10],
        year=int(proposal.get("year") or date.today().year),
        subject_id=int(proposal["subject_id"]) if proposal.get("subject_id") else None,
        roadmap_id=int(proposal["roadmap_id"]) if proposal.get("roadmap_id") else None,
        target_date=_parse_date(proposal.get("target_date")),
        progress_percentage=0.0,
    )
    db.add(goal)
    db.flush()
    return goal


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def goal_progress(db: Session, user_id: int, goal_id: int) -> dict | None:
    """Goal progress from roadmap topic completion (phrase 71)."""
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if goal is None:
        return None
    if not goal.subject_id:
        return {"goal_id": goal.id, "progress_percentage": goal.progress_percentage or 0.0, "detail": None}
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == goal.subject_id)
        .all()
    )
    mastery = mastery_by_topic(db, user_id, [t.id for t in topics])
    mastered = sum(1 for m in mastery.values() if m["classification"] == "strong")
    pct = round(mastered / len(topics) * 100, 1) if topics else 0.0
    goal.progress_percentage = pct
    db.flush()
    return {
        "goal_id": goal.id,
        "title": goal.title,
        "progress_percentage": pct,
        "topics_mastered": mastered,
        "topics_total": len(topics),
        "detail": {"subject_id": goal.subject_id},
    }


def list_goals(db: Session, user_id: int) -> list[dict]:
    rows = db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.id.desc()).all()
    return [
        {
            "id": g.id,
            "title": g.title,
            "quarter": g.quarter,
            "year": g.year,
            "subject_id": g.subject_id,
            "roadmap_id": g.roadmap_id,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "progress_percentage": g.progress_percentage or 0.0,
            "is_completed": bool(g.is_completed),
        }
        for g in rows
    ]


__all__ = [
    "week_start",
    "get_or_generate",
    "list_reflections",
    "apply_plan_adjustments",
    "derive_goals",
    "confirm_derived_goal",
    "goal_progress",
    "list_goals",
]
