"""Idea 99 — predictive analytics & learning-trajectory forecasting.

Time-series over ``learning_events`` + ``user_memory`` (phrase 81):
- **EWMA** (default): exponentially-weighted moving average of per-day mastery
  per subject; ``KB_FORECAST_MODEL=linear`` swaps in least-squares regression
  (phrase 82).
- **Exam-readiness** (phrase 83): the forecast value, decay-weighted by days
  until the nearest exam.
- **At-risk flag** (phrase 84): readiness below ``KB_FORECAST_RISK_THRESHOLD``.
- **Early-warning alerts** (phrase 86): coalesced per-subject notifications on
  a flip to at-risk — never re-fires while the subject stays at risk.

``user_memory`` and ``learning_events`` schemas are only read here (phrase 90).
Deterministic — pure math, no LLM calls.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Course, Exam, LearningEvent, Notification, Topic
from app.services.kb import utcnow

# EWMA smoothing factor + linear-regression fallback constants.
ALPHA = 0.3
# Mastery boost for time-based events (mirrors mastery.py pacing).
SESSION_BOOST = 0.03


# --------------------------------------------------------------------------- #
# Series math (phrase 82)
# --------------------------------------------------------------------------- #


def ewma_series(values: list[float], alpha: float = ALPHA) -> list[float]:
    """Exponentially-weighted moving average over a value sequence."""
    out: list[float] = []
    prev = None
    for v in values:
        prev = v if prev is None else alpha * v + (1 - alpha) * prev
        out.append(round(prev, 4))
    return out


def linear_forecast(values: list[float], horizon: int = 1) -> float:
    """Least-squares slope + intercept projected ``horizon`` steps ahead."""
    n = len(values)
    if n == 0:
        return 0.0
    if n == 1:
        return round(values[0], 4)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denom if denom else 0.0
    intercept = y_mean - slope * x_mean
    projected = intercept + slope * (n - 1 + horizon)
    return round(max(0.0, min(1.0, projected)), 4)


def _event_mastery_value(event: LearningEvent) -> float | None:
    """Per-event mastery signal (0–1), None for events that carry none."""
    v = float(event.value or 0.0)
    if event.event_type == "quiz":
        return max(0.0, min(1.0, v))
    if event.event_type == "revision":
        return max(0.0, min(1.0, v))
    if event.event_type in ("session", "study"):
        return min(1.0, SESSION_BOOST)
    return None


# --------------------------------------------------------------------------- #
# Per-subject trajectory (phrase 85)
# --------------------------------------------------------------------------- #


def subject_series(db: Session, user_id: int, subject_id: int) -> list[dict]:
    """Daily mastery series for a subject: ``[{date, value, events}]``."""
    topic_ids = [
        t.id
        for t in db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    ]
    if not topic_ids:
        return []
    events = (
        db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.topic_id.in_(topic_ids),
        )
        .order_by(LearningEvent.created_at.asc())
        .all()
    )
    by_day: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for e in events:
        value = _event_mastery_value(e)
        if value is None:
            continue
        day = (e.created_at or utcnow()).date().isoformat()
        by_day.setdefault(day, []).append(value)
        counts[day] = counts.get(day, 0) + 1
    series = [
        {
            "date": day,
            "value": round(sum(v) / len(v), 4),
            "events": counts[day],
        }
        for day, v in sorted(by_day.items())
    ]
    return series


def trajectory(db: Session, user_id: int, subject_id: int) -> dict:
    """Trajectory points + forecast + readiness + at-risk (phrases 83–85)."""
    series = subject_series(db, user_id, subject_id)
    values = [s["value"] for s in series]
    if not values:
        return {
            "subject_id": subject_id,
            "points": [],
            "model": settings.kb_forecast_model,
            "forecast": 0.0,
            "readiness": 0.0,
            "at_risk": True,
            "risk_threshold": settings.kb_forecast_risk_threshold,
            "exam_days_until": _exam_days(db, user_id, subject_id),
            "series_points": 0,
        }

    if settings.kb_forecast_model == "linear":
        forecast = linear_forecast(values)
    else:
        smoothed = ewma_series(values)
        forecast = smoothed[-1]
        series = [
            {**s, "ewma": sm}
            for s, sm in zip(series, smoothed)
        ]

    exam_days = _exam_days(db, user_id, subject_id)
    readiness = _readiness(forecast, exam_days)
    threshold = settings.kb_forecast_risk_threshold
    return {
        "subject_id": subject_id,
        "points": series,
        "model": settings.kb_forecast_model,
        "forecast": round(forecast, 4),
        "readiness": readiness,
        "at_risk": readiness < threshold,
        "risk_threshold": threshold,
        "exam_days_until": exam_days,
        "series_points": len(series),
    }


def _readiness(forecast: float, exam_days: int | None) -> float:
    """Weighted forecast vs exam date (phrase 83)."""
    if exam_days is None:
        return round(forecast, 4)
    # Closer to the exam → readiness depends more on the current level.
    proximity = max(0.0, 1.0 - exam_days / 30.0)
    return round(forecast * (1.0 - 0.4 * proximity), 4)


def _exam_days(db: Session, user_id: int, subject_id: int) -> int | None:
    """Nearest upcoming exam for a curriculum subject.

    ``Exam.course_id`` points at ``courses.id`` (not ``curriculum_subjects.id``),
    so the subject must be resolved through ``Course.curriculum_subject_id``.
    """
    exam = (
        db.query(Exam)
        .join(Course, Course.id == Exam.course_id)
        .filter(
            Course.curriculum_subject_id == subject_id,
            Course.user_id == user_id,
            Exam.date >= date.today(),
        )
        .order_by(Exam.date.asc())
        .first()
    )
    if exam is None:
        return None
    return max(0, (exam.date - date.today()).days)


# --------------------------------------------------------------------------- #
# At-risk alerts (phrase 86)
# --------------------------------------------------------------------------- #


def check_at_risk(db: Session, user_id: int, subject_id: int) -> dict:
    """Evaluate at-risk state; fire one coalesced notification per flip."""
    traj = trajectory(db, user_id, subject_id)
    if not traj["at_risk"]:
        return {"subject_id": subject_id, "at_risk": False, "alerted": False}

    marker = f"at-risk:{subject_id}"
    already = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.kind == "forecast",
            Notification.ref_type == marker,
        )
        .first()
    )
    alerted = False
    if already is None:
        db.add(
            Notification(
                user_id=user_id,
                kind="forecast",
                title="Early warning: a subject is at risk",
                body=(
                    f"Readiness for this subject is {traj['readiness']:.0%} "
                    f"(below the {traj['risk_threshold']:.0%} threshold). "
                    "Consider shifting study time here."
                ),
                ref_type=marker,
                ref_id=subject_id,
            )
        )
        # Flush so the ``already`` guard sees the row on the next call (the
        # shared session is autoflush=False, so a query alone would miss the
        # pending insert and re-fire the alert).
        db.flush()
        alerted = True
    return {"subject_id": subject_id, "at_risk": True, "alerted": alerted}


def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Job-style sweep: evaluate + alert every subject with topics."""
    subject_ids = {
        t.subject_id
        for t in db.query(Topic).filter(Topic.user_id == user_id).all()
        if t.subject_id
    }
    alerted = 0
    at_risk = 0
    for sid in sorted(subject_ids):
        result = check_at_risk(db, user_id, sid)
        if result["at_risk"]:
            at_risk += 1
        if result["alerted"]:
            alerted += 1
    if alerted:
        db.commit()
    return {"processed": len(subject_ids), "at_risk": at_risk, "alerted": alerted}


__all__ = [
    "ewma_series",
    "linear_forecast",
    "trajectory",
    "check_at_risk",
    "run",
]
