"""Gap Analysis history — a compact log of analyses per scope over time.

Every time a gap analysis is computed or re-run (course/subject OR career
goal), a snapshot is appended here. The frontend uses it to show how a
subject's gaps changed across re-analyses: new gaps, resolved gaps, level
improvements, and coverage trends.

Snapshots are *compact* by design: per-gap/per-strength summaries + counts,
not the full (large) analysis payload — that is enough to diff two snapshots
and keeps the table tiny. Only the most recent ``HISTORY_CAP`` snapshots per
scope are kept (the latest full analysis always lives in the cache tables).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import GapAnalysisHistory

# Keep at most this many snapshots per (user, scope).
HISTORY_CAP = 25


def _compact_snapshot(payload: dict) -> dict:
    """Reduce a full analysis payload to the diffable snapshot shape."""
    gaps = payload.get("gaps") or []
    strengths = payload.get("strengths") or []
    next_item = payload.get("next") or {}
    return {
        "analyzed_at": payload.get("analyzed_at"),
        "document_count": payload.get("document_count"),
        "gap_count": len(gaps),
        "strength_count": len(strengths),
        "coverage": payload.get("coverage"),
        "next": next_item.get("name") if isinstance(next_item, dict) else None,
        "gaps": [
            {
                "name": g.get("name"),
                "level": g.get("level"),
                "priority": g.get("priority"),
                "domain": g.get("domain"),
            }
            for g in gaps
            if isinstance(g, dict) and g.get("name")
        ],
        "strengths": [
            {"name": s.get("name"), "level": s.get("level")}
            for s in strengths
            if isinstance(s, dict) and s.get("name")
        ],
    }


def record_gap_history(
    db: Session,
    user_id: int,
    *,
    course_id: int | None = None,
    goal_key: str | None = None,
    payload: dict,
) -> None:
    """Append one snapshot for a scope, pruning to the newest ``HISTORY_CAP``.

    Called from the cache-save paths (first compute AND explicit re-analyze)
    so every analysis becomes a history entry. ``course_id`` XOR ``goal_key``
    must be provided to identify the scope.
    """
    scope_type = "course" if course_id is not None else "goal"
    analyzed_at = payload.get("analyzed_at")
    try:
        analyzed = (
            datetime.fromisoformat(analyzed_at)
            if isinstance(analyzed_at, str)
            else datetime.now(timezone.utc)
        )
    except ValueError:
        analyzed = datetime.now(timezone.utc)

    db.add(
        GapAnalysisHistory(
            user_id=user_id,
            scope_type=scope_type,
            course_id=course_id,
            goal_key=goal_key,
            snapshot_json=json.dumps(_compact_snapshot(payload), default=str),
            analyzed_at=analyzed,
        )
    )
    # Make the new snapshot visible to the prune query below — the app's
    # session is created with ``autoflush=False``, so a pending INSERT would
    # otherwise be invisible and the cap would never trigger.
    db.flush()

    # Prune: keep only the newest HISTORY_CAP rows for this scope.
    q = db.query(GapAnalysisHistory.id).filter(
        GapAnalysisHistory.user_id == user_id,
        GapAnalysisHistory.scope_type == scope_type,
    )
    if course_id is not None:
        q = q.filter(GapAnalysisHistory.course_id == course_id)
    else:
        q = q.filter(GapAnalysisHistory.goal_key == goal_key)
    ids = [row[0] for row in q.order_by(desc(GapAnalysisHistory.analyzed_at)).all()]
    if len(ids) > HISTORY_CAP:
        db.query(GapAnalysisHistory).filter(
            GapAnalysisHistory.id.in_(ids[HISTORY_CAP:])
        ).delete(synchronize_session=False)
    db.commit()


def list_gap_history(
    db: Session,
    user_id: int,
    *,
    course_id: int | None = None,
    goal_key: str | None = None,
) -> list[dict]:
    """Snapshots for a scope, oldest → newest (chronological for diffing)."""
    scope_type = "course" if course_id is not None else "goal"
    q = db.query(GapAnalysisHistory).filter(
        GapAnalysisHistory.user_id == user_id,
        GapAnalysisHistory.scope_type == scope_type,
    )
    if course_id is not None:
        q = q.filter(GapAnalysisHistory.course_id == course_id)
    else:
        q = q.filter(GapAnalysisHistory.goal_key == goal_key)
    rows = q.order_by(GapAnalysisHistory.analyzed_at.asc()).all()
    return [json.loads(r.snapshot_json or "{}") for r in rows]


def delete_course_history(db: Session, user_id: int, course_id: int) -> None:
    """Drop a course's history when the course is deleted (no orphaned rows)."""
    db.query(GapAnalysisHistory).filter(
        GapAnalysisHistory.user_id == user_id,
        GapAnalysisHistory.scope_type == "course",
        GapAnalysisHistory.course_id == course_id,
    ).delete()
    db.commit()
