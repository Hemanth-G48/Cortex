"""Focus/Readiness Loop workflow — \"what should I study right now\".

Read-mostly, exam-aware readiness board that combines two existing services:

- **``forecast.trajectory``** — per-subject forecast/readiness/at-risk + days
  until the nearest exam (pure math, no LLM).
- **``next_action.recommend``** — top topics to study now with explainable
  reasons (weakness, due reviews, concept gaps, exam proximity).

``focus_board`` merges them into one deterministic payload ordered by urgency:
exam-approaching at-risk subjects surface first, then the recommender's top
topics. Opening the page never runs an LLM call and never mutates data.

``start_focus_session`` is the explicit action: it delegates to the standard
micro-session factory (``sessions.build_session`` + ``start_session``) so the
started session reuses the Pomodoro/mastery machinery.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Topic
from app.services.kb import forecast as forecast_svc
from app.services.kb import next_action as next_action_svc
from app.services.kb import sessions as sessions_svc


def _subject_rows(db: Session, user_id: int) -> list[dict]:
    """Per-subject readiness rows (trajectory + exam proximity), at-risk first."""
    subject_ids = {
        t.subject_id
        for t in db.query(Topic).filter(Topic.user_id == user_id).all()
        if t.subject_id
    }
    rows = []
    for sid in sorted(subject_ids):
        traj = forecast_svc.trajectory(db, user_id, sid)
        rows.append(
            {
                "subject_id": sid,
                "forecast": traj["forecast"],
                "readiness": traj["readiness"],
                "at_risk": traj["at_risk"],
                "risk_threshold": traj.get("risk_threshold"),
                "exam_days_until": traj.get("exam_days_until"),
                "series_points": traj.get("series_points"),
                "model": traj.get("model"),
            }
        )
    rows.sort(
        key=lambda r: (
            0 if r["at_risk"] else 1,  # at-risk first
            r["exam_days_until"] if r["exam_days_until"] is not None else 10**6,  # then closest exam
        )
    )
    return rows


def focus_board(db: Session, user_id: int, *, limit: int = 5) -> dict:
    """Read-only readiness board (never calls the LLM, never mutates)."""
    subjects = _subject_rows(db, user_id)
    recommendations = next_action_svc.recommend(db, user_id, limit=limit)

    # Attach subject readiness to each recommendation for the UI.
    readiness_by_subject = {s["subject_id"]: s for s in subjects}
    for rec in recommendations:
        rec["subject_readiness"] = readiness_by_subject.get(rec.get("subject_id"))

    at_risk = [s for s in subjects if s["at_risk"]]
    return {
        "subjects": subjects,
        "recommendations": recommendations,
        "at_risk_count": len(at_risk),
        "exam_approaching": [
            s for s in subjects if s["exam_days_until"] is not None and s["exam_days_until"] <= 14
        ],
        "total_subjects": len(subjects),
    }


def start_focus_session(
    db: Session,
    user_id: int,
    topic_id: int,
    *,
    duration_mins: int | None = None,
) -> dict:
    """Explicit action: build + start a micro-session on a recommended topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if topic is None:
        raise ValueError("Topic not found")
    session = sessions_svc.build_session(db, user_id, topic, duration_mins=duration_mins)
    sessions_svc.start_session(db, user_id, session)
    db.flush()
    return sessions_svc.session_dict(session, topic)
