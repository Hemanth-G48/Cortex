"""Idea 100 — self-improving assistant + observability.

``log_event`` is the single write path for every AI interaction (Rule A: every
AI interaction is measured). ``weekly_report`` aggregates cost/latency/quality
for the weekly notification; ``prompt_versions`` makes templates A/B-able.

The meter is a no-op when ``KB_AI_LOG_ENABLED=false`` (tests/CI can turn it off
for speed) — but it never raises, so logging can never break a feature.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AiLog, PromptVersion
from app.services.kb import KbService, utcnow

# Features metered by Phase 10 surfaces.
FEATURES = (
    "tutor", "agent", "grading", "explain", "summary",
    "recommend", "forecast", "research", "reflection",
)

# Rough cost model (per 1k tokens) — used only for relative trend reporting.
COST_PER_1K_IN = 0.0005
COST_PER_1K_OUT = 0.0015


def log_event(
    db: Session,
    user_id: int,
    *,
    feature: str,
    request: str | None = None,
    response: str | None = None,
    retrieval: dict | None = None,
    latency_ms: int = 0,
    tokens: int = 0,
    cost_estimate: float | None = None,
    feedback: int = 0,
    faithfulness_score: float | None = None,
) -> AiLog | None:
    """Record one AI interaction (best-effort, never raises)."""
    if not KbService.bool_setting("KB_AI_LOG_ENABLED", True):
        return None
    feature = feature if feature in FEATURES else "tutor"
    row = AiLog(
        user_id=user_id,
        feature=feature,
        request=(request or "")[:4000],
        retrieval=KbService.json_dumps(retrieval) if retrieval else None,
        response=(response or "")[:4000],
        latency_ms=max(0, int(latency_ms)),
        tokens=max(0, int(tokens)),
        cost_estimate=max(0.0, float(cost_estimate if cost_estimate is not None else _estimate_cost(tokens))),
        feedback=max(-1, min(1, int(feedback))),
        faithfulness_score=(
            max(0.0, min(1.0, float(faithfulness_score)))
            if faithfulness_score is not None
            else None
        ),
    )
    db.add(row)
    try:
        # Savepoint so a failed meter write never rolls back the caller's own
        # pending work in the same request transaction (Rule: never breaks flow).
        with db.begin_nested():
            db.flush()
    except Exception:  # noqa: BLE001 — the meter must never break the flow
        return None
    return row


def _estimate_cost(tokens: int) -> float:
    """Rough cost estimate from token count (relative metric only)."""
    return round((int(tokens) * (COST_PER_1K_IN + COST_PER_1K_OUT)) / 1000.0, 6)


def set_feedback(db: Session, user_id: int, log_id: int, feedback: int) -> AiLog | None:
    """Record explicit user feedback (-1 | 0 | 1) on a logged interaction."""
    row = db.query(AiLog).filter(AiLog.id == log_id, AiLog.user_id == user_id).first()
    if row is None:
        return None
    row.feedback = max(-1, min(1, int(feedback)))
    db.flush()
    return row


def recent_logs(db: Session, user_id: int, limit: int = 200) -> list[dict]:
    """Latest AI interactions for the user (dashboard + observability)."""
    rows = (
        db.query(AiLog)
        .filter(AiLog.user_id == user_id)
        .order_by(AiLog.created_at.desc(), AiLog.id.desc())
        .limit(limit)
        .all()
    )
    return [_log_dict(r) for r in rows]


def _log_dict(r: AiLog) -> dict:
    return {
        "id": r.id,
        "feature": r.feature,
        "request": r.request,
        "response": r.response,
        "latency_ms": r.latency_ms,
        "tokens": r.tokens,
        "cost_estimate": r.cost_estimate,
        "feedback": r.feedback,
        "faithfulness_score": r.faithfulness_score,
        "retrieval": KbService.json_loads(r.retrieval),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def aggregate(db: Session, user_id: int | None = None, *, since: datetime | None = None) -> dict:
    """Cost/latency/quality aggregation (phrase 97 dashboard payload).

    ``user_id=None`` aggregates across all users (admin observability).
    """
    q = db.query(AiLog)
    if user_id is not None:
        q = q.filter(AiLog.user_id == user_id)
    if since is not None:
        q = q.filter(AiLog.created_at >= since)
    rows = q.all()

    total = len(rows)
    if not rows:
        return {
            "total": 0, "cost_estimate": 0.0, "avg_latency_ms": 0, "p95_latency_ms": 0,
            "feedback": {"positive": 0, "negative": 0, "neutral": total},
            "avg_faithfulness": None, "by_feature": {}, "tokens": 0,
        }

    latencies = sorted(r.latency_ms or 0 for r in rows)
    p95 = latencies[max(0, int(round(len(latencies) * 0.95)) - 1)] if latencies else 0
    feedbacks = [r.feedback or 0 for r in rows]
    faiths = [r.faithfulness_score for r in rows if r.faithfulness_score is not None]
    by_feature: dict[str, dict] = {}
    for r in rows:
        f = by_feature.setdefault(
            r.feature,
            {"count": 0, "cost_estimate": 0.0, "latency_sum_ms": 0, "feedback_sum": 0},
        )
        f["count"] += 1
        f["cost_estimate"] += r.cost_estimate or 0.0
        f["latency_sum_ms"] += r.latency_ms or 0
        f["feedback_sum"] += r.feedback or 0

    return {
        "total": total,
        "cost_estimate": round(sum(r.cost_estimate or 0.0 for r in rows), 6),
        "tokens": sum(r.tokens or 0 for r in rows),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
        "p95_latency_ms": p95,
        "feedback": {
            "positive": feedbacks.count(1),
            "negative": feedbacks.count(-1),
            "neutral": feedbacks.count(0),
        },
        "avg_faithfulness": round(sum(faiths) / len(faiths), 4) if faiths else None,
        "by_feature": {
            name: {
                "count": v["count"],
                "cost_estimate": round(v["cost_estimate"], 6),
                "avg_latency_ms": round(v["latency_sum_ms"] / v["count"], 1),
                "feedback": round(v["feedback_sum"] / v["count"], 3),
            }
            for name, v in sorted(by_feature.items())
        },
    }


def weekly_report(db: Session, user_id: int, *, week_start: date | None = None) -> dict:
    """Weekly cost/latency/quality summary (phrase 95). Deterministic aggregation.

    Returns the report payload; callers push it as a coalesced notification.
    """
    week_start = week_start or _monday()
    since = datetime.combine(week_start, datetime.min.time())
    agg = aggregate(db, user_id, since=since)
    failures = (
        db.query(AiLog)
        .filter(
            AiLog.user_id == user_id,
            AiLog.created_at >= since,
            AiLog.faithfulness_score.is_not(None),
            AiLog.faithfulness_score < 0.5,
        )
        .count()
    )
    return {
        "week_start": week_start.isoformat(),
        "aggregate": agg,
        "top_failures": failures,
        "generated_at": utcnow().isoformat(),
    }


def _monday(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


# --------------------------------------------------------------------------- #
# Prompt versioning (phrase 96)
# --------------------------------------------------------------------------- #


def get_prompt(db: Session, feature: str, template: str, version: int | None = None) -> tuple[str, int]:
    """Resolve a prompt template against prompt_versions (A/B-able).

    Upserts the active version on first use; returns ``(template, version)`` so
    the caller can log which version it used. ``version=None`` → the active one.
    """
    row = (
        db.query(PromptVersion)
        .filter(
            PromptVersion.feature == feature,
            PromptVersion.is_active == 1,
        )
        .order_by(PromptVersion.id.desc())
        .first()
    )
    if row is None:
        row = PromptVersion(feature=feature, version=1, template=template, is_active=1)
        db.add(row)
        db.flush()
        return template, 1
    if version is not None:
        pinned = (
            db.query(PromptVersion)
            .filter(PromptVersion.feature == feature, PromptVersion.version == version)
            .first()
        )
        if pinned is not None:
            return pinned.template, pinned.version
    return row.template, row.version


def pin_prompt(db: Session, feature: str, template: str, version: int | None = None) -> PromptVersion:
    """Activate ``version`` (or bump a new version) for a feature template."""
    if version is not None:
        row = (
            db.query(PromptVersion)
            .filter(PromptVersion.feature == feature, PromptVersion.version == version)
            .first()
        )
        if row is not None:
            db.query(PromptVersion).filter(PromptVersion.feature == feature).update(
                {PromptVersion.is_active: 0}
            )
            row.is_active = 1
            db.flush()
            return row
    max_v = (
        db.query(PromptVersion)
        .filter(PromptVersion.feature == feature)
        .order_by(PromptVersion.version.desc())
        .first()
    )
    new_version = (max_v.version if max_v else 0) + 1
    row = PromptVersion(feature=feature, version=new_version, template=template, is_active=1)
    db.add(row)
    db.flush()
    return row


__all__ = [
    "log_event",
    "set_feedback",
    "recent_logs",
    "aggregate",
    "weekly_report",
    "get_prompt",
    "pin_prompt",
]
