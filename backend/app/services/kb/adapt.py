"""Phase 8 adaptive learning paths (Idea 80, phrases 91–97).

``adapt_roadmap`` recomputes a subject's Phase 5 roadmap from the current state
of the learner:

- **Skip mastered topics** — a topic whose mastery classification is ``strong``
  (score ≥ 0.75 with enough evidence) leaves the plan, *unless* it is due for a
  spaced-repetition review or carries a concept gap.
- **Gap topics first** — concepts ranked by Group 2 gap evidence pull their
  topic to the front, so the newly detected gap is inserted into the nearest
  week (phrase 97).
- **Due reviews next** — topics with due ``RevisionSchedule`` rows are promoted
  ahead of cold material.
- **Remaining topics** weakest-first within the unit order.

Every recompute writes a new ``Roadmap`` version via ``roadmap.generate_roadmap
(..., topic_ids=...)`` and archives the previous active one (phrase 95), and
returns an explainable ``{added_reviews, removed_topics, reordered[], reason}``
diff (phrase 93).

Per-user scoping is non-negotiable — every query filters ``user_id``.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import CurriculumUnit, Topic
from app.services.kb import KbService
from app.services.kb.gaps import _topic_concept_index, concept_gaps
from app.services.kb.mastery import mastery_by_topic
from app.services.kb.revision import due_reviews
from app.services.kb.roadmap import generate_roadmap, get_active

# A gap topic that scores above this gap-score is an aggressive "insert now".
GAP_INSERT_MIN = 0.15


def _unit_order(db: Session, subject_id: int) -> dict[int, int]:
    return {
        u.id: i
        for i, u in enumerate(
            db.query(CurriculumUnit)
            .filter(CurriculumUnit.subject_id == subject_id)
            .order_by(CurriculumUnit.unit_number.asc())
            .all(),
            start=1,
        )
    }


def _topic_gap_scores(db: Session, user_id: int) -> dict[int, float]:
    """topic_id -> best concept-gap score (0 when the topic has no gap)."""
    gaps = {g["concept_id"]: g for g in concept_gaps(db, user_id, limit=100)}
    if not gaps:
        return {}
    topic_concept = _topic_concept_index(db, user_id)
    out: dict[int, float] = {}
    for tid, concept_ids in topic_concept.items():
        scores = [gaps[c]["score"] for c in concept_ids if c in gaps]
        if scores:
            out[tid] = max(scores)
    return out


def _order_topics(
    topics: list[Topic],
    mastery: dict[int, dict],
    due_set: set[int],
    gap_scores: dict[int, float],
    unit_order: dict[int, int],
) -> list[int]:
    """Deterministic adapted ordering: gaps → due → weakest-first remainder."""
    mastered = {
        t.id for t in topics
        if mastery.get(t.id, {}).get("classification") == "strong"
    }
    gap_ids = {
        t.id for t in topics
        if gap_scores.get(t.id, 0.0) >= GAP_INSERT_MIN
    }

    # Gap topics, highest gap score first (inserted into the nearest week).
    gap = sorted(
        [t for t in topics if t.id in gap_ids],
        key=lambda t: (-gap_scores[t.id], t.id),
    )
    # Due-review topics not already a gap, earliest-created first.
    due = sorted(
        [t for t in topics if t.id in due_set and t.id not in gap_ids],
        key=lambda t: t.id,
    )
    # Everything else: skip mastered, order weakest-first within unit.
    remaining = [
        t for t in topics
        if t.id not in mastered
        and t.id not in gap_ids
        and t.id not in due_set
    ]

    def _remain_key(t: Topic) -> tuple[int, float, int]:
        unit = unit_order.get(t.unit_id or 0, 0)
        score = mastery.get(t.id, {}).get("score", 0.0)
        return (unit, score, t.id)  # ascending score ⇒ weakest first

    remaining.sort(key=_remain_key)
    return [t.id for t in gap + due + remaining]


def _plan_topic_ids(roadmap) -> list[int]:
    """Ordered topic ids from a persisted Roadmap's plan_json, best-effort."""
    if roadmap is None:
        return []
    plan = KbService.json_loads(roadmap.plan_json) or {}
    out: list[int] = []
    for week in plan.get("weeks", []):
        out.extend(week.get("topic_ids", []))
    return out


def _diff(
    db: Session,
    user_id: int,
    subject_id: int,
    ordered: list[int],
) -> dict:
    """Explainable plan diff vs the previous active version (phrase 93)."""
    prev_ids = _plan_topic_ids(get_active(db, user_id, subject_id))
    prev_set = set(prev_ids)
    new_set = set(ordered)

    added = [tid for tid in ordered if tid not in prev_set]
    removed = [tid for tid in prev_ids if tid not in new_set]
    prev_index = {tid: i for i, tid in enumerate(prev_ids)}
    reordered = [
        tid for tid in ordered
        if tid in prev_index and prev_index[tid] != ordered.index(tid)
    ]

    reasons: list[str] = []
    if removed:
        reasons.append(f"{len(removed)} topic(s) mastered or skipped")
    if added:
        reasons.append(f"{len(added)} review(s) added for gaps/due")
    if reordered:
        reasons.append(f"{len(reordered)} topic(s) reordered")
    if not reasons:
        reasons.append("no material change")

    return {
        "added_reviews": len(added),
        "added_topic_ids": added,
        "removed_topics": removed,
        "removed_topic_ids": removed,
        "reordered": reordered,
        "reason": "; ".join(reasons),
        "reasons": reasons,
    }


def adapt_roadmap(
    db: Session,
    user_id: int,
    subject_id: int,
    *,
    weekly_budget: int | None = None,
    deadline: date | None = None,
) -> dict:
    """Recompute the subject's roadmap from current mastery + due + gaps.

    Always writes a new version (phrase 95). Returns the roadmap summary plus
    the explainable diff. Deterministic: no LLM calls, so no budget spend.
    """
    topics = (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == subject_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )
    if not topics:
        return {
            "roadmap_id": None,
            "version": None,
            "topic_ids": [],
            "diff": _diff(db, user_id, subject_id, []),
        }

    topic_ids = [t.id for t in topics]
    mastery = mastery_by_topic(db, user_id, topic_ids)
    due = {d["topic_id"] for d in due_reviews(db, user_id, on=date.today()) if d["subject_id"] == subject_id}
    gap_scores = _topic_gap_scores(db, user_id)
    unit_order = _unit_order(db, subject_id)

    ordered = _order_topics(topics, mastery, due, gap_scores, unit_order)
    diff = _diff(db, user_id, subject_id, ordered)

    roadmap = generate_roadmap(
        db,
        user_id,
        subject_id,
        weekly_budget=weekly_budget,
        deadline=deadline,
        topic_ids=ordered,
    )
    db.commit()
    return {
        "roadmap_id": roadmap.id,
        "version": roadmap.version,
        "status": roadmap.status,
        "topic_ids": ordered,
        "diff": diff,
    }


def should_adapt(db: Session, user_id: int, subject_id: int) -> list[str]:
    """Recompute triggers (phrase 92): non-empty when adaptation is warranted.

    Observable signals only — a topic was mastered and would be skipped, new
    review(s) would be inserted for gaps/due work, or the plan would reorder.
    Exam-date changes surface through the ``deadline`` the caller passes to
    ``adapt_roadmap``; historical diffing against archived versions is left to
    Phase 9 automation.
    """
    topics = (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == subject_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )
    if not topics:
        return []
    topic_ids = [t.id for t in topics]
    mastery = mastery_by_topic(db, user_id, topic_ids)
    due = {d["topic_id"] for d in due_reviews(db, user_id, on=date.today()) if d["subject_id"] == subject_id}
    gap_scores = _topic_gap_scores(db, user_id)
    ordered = _order_topics(topics, mastery, due, gap_scores, _unit_order(db, subject_id))
    return _diff(db, user_id, subject_id, ordered)["reasons"]
