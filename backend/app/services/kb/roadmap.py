"""Phase 5 learning roadmap generation (Idea 47, phrases 61–70).

Algorithmic (no LLM needed — deterministic by design): topological order over
the topic DAG (Idea 46 helpers) is the backbone; topics are bucketed into weeks
by their ``first_pass_mins`` against a weekly time budget; an optional deadline
caps the number of weeks. Every generation writes a new ``Roadmap`` row and
archives the previous active one (versioning = new rows).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import CurriculumUnit, Roadmap, Topic
from app.services.kb import KbService, utcnow
from app.services.kb.dependencies import topological_order

DEFAULT_WEEKLY_BUDGET = 300  # minutes/week (≈5 focused hours)
MIN_WEEKLY_BUDGET = 60


def _estimate_minutes(topic: Topic) -> int:
    return max(5, topic.first_pass_mins or 60)


def generate_roadmap(
    db: Session,
    user_id: int,
    subject_id: int,
    *,
    weekly_budget: int | None = None,
    deadline: date | None = None,
    topic_ids: list[int] | None = None,
) -> Roadmap:
    """Create a new active roadmap version (phrases 63–67).

    ``topic_ids`` (Phase 8 Idea 80): caller-supplied topic ordering. When
    provided, the exact order is preserved (adaptation injects gap/due topics);
    otherwise the topological order with unit tie-breaking is computed here.
    """
    budget = weekly_budget or DEFAULT_WEEKLY_BUDGET
    budget = max(MIN_WEEKLY_BUDGET, budget)

    topics = (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == subject_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )
    if topic_ids is not None:
        # Caller-supplied order: drop any ids that are not this subject's topics.
        id_to_topic = {t.id: t for t in topics}
        stable_order = [tid for tid in topic_ids if tid in id_to_topic]
        weeks = _bucket(stable_order, budget, id_to_topic) if not deadline else _spread(
            stable_order, max(1, ((deadline - date.today()).days + 6) // 7), id_to_topic
        )
        plan = {
            "weekly_budget_minutes": budget,
            "weeks": [
                {
                    "week": i + 1,
                    "topic_ids": [t.id for t in week],
                    "topics": [t.name for t in week],
                    "est_mins": sum(_estimate_minutes(t) for t in week),
                }
                for i, week in enumerate(weeks)
            ],
        }
        return _persist(db, user_id, subject_id, plan)

    # unit order informs tie-breaking for unrelated topics
    unit_order: dict[int, int] = {}
    for i, unit in enumerate(
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id)
        .order_by(CurriculumUnit.unit_number.asc())
        .all(),
        start=1,
    ):
        unit_order[unit.id] = i
    ordered_ids = topological_order(db, user_id, subject_id, [t.id for t in topics])
    id_to_topic = {t.id: t for t in topics}

    def sort_key(tid: int) -> tuple[int, int]:
        t = id_to_topic[tid]
        return (unit_order.get(t.unit_id or 0, 0), t.unit_id or 0, t.id)

    stable_order = sorted(ordered_ids, key=sort_key)

    # Deadline-aware: spread across the available weeks (phrase 65).
    if deadline:
        today = date.today()
        weeks_available = max(1, ((deadline - today).days + 6) // 7)
        weeks = _spread(stable_order, weeks_available, id_to_topic)
    else:
        weeks = _bucket(stable_order, budget, id_to_topic)

    plan = {
        "weekly_budget_minutes": budget,
        "weeks": [
            {
                "week": i + 1,
                "topic_ids": [t.id for t in week],
                "topics": [t.name for t in week],
                "est_mins": sum(_estimate_minutes(t) for t in week),
            }
            for i, week in enumerate(weeks)
        ],
    }
    return _persist(db, user_id, subject_id, plan)


def _persist(db: Session, user_id: int, subject_id: int, plan: dict) -> Roadmap:
    """Archive previous actives and insert the new active version (phrase 62)."""
    db.query(Roadmap).filter(
        Roadmap.user_id == user_id,
        Roadmap.subject_id == subject_id,
        Roadmap.status == "active",
    ).update({"status": "archived"}, synchronize_session=False)

    latest = (
        db.query(Roadmap)
        .filter(Roadmap.user_id == user_id, Roadmap.subject_id == subject_id)
        .order_by(Roadmap.version.desc())
        .first()
    )
    version = (latest.version if latest else 0) + 1
    roadmap = Roadmap(
        user_id=user_id,
        subject_id=subject_id,
        version=version,
        status="active",
        plan_json=KbService.json_dumps(plan),
    )
    db.add(roadmap)
    db.flush()
    return roadmap


def _bucket(
    topic_ids: list[int], budget: int, id_to_topic: dict[int, Topic]
) -> list[list[Topic]]:
    """Fill weeks up to the budget, respecting order (phrase 64)."""
    weeks: list[list[Topic]] = []
    current: list[Topic] = []
    current_total = 0
    for tid in topic_ids:
        topic = id_to_topic[tid]
        est = _estimate_minutes(topic)
        if current and current_total + est > budget:
            weeks.append(current)
            current = []
            current_total = 0
        current.append(topic)
        current_total += est
    if current:
        weeks.append(current)
    return weeks


def _spread(
    topic_ids: list[int], weeks_available: int, id_to_topic: dict[int, Topic]
) -> list[list[Topic]]:
    """Distribute topics as evenly as possible over the available weeks."""
    if not topic_ids:
        return []
    chunk_size = max(1, -(-len(topic_ids) // weeks_available))  # ceil division
    return [
        [id_to_topic[tid] for tid in topic_ids[i : i + chunk_size]]
        for i in range(0, len(topic_ids), chunk_size)
    ]


def get_active(db: Session, user_id: int, subject_id: int) -> Roadmap | None:
    return (
        db.query(Roadmap)
        .filter(
            Roadmap.user_id == user_id,
            Roadmap.subject_id == subject_id,
            Roadmap.status == "active",
        )
        .order_by(Roadmap.version.desc())
        .first()
    )


def get_versions(db: Session, user_id: int, subject_id: int) -> list[Roadmap]:
    return (
        db.query(Roadmap)
        .filter(Roadmap.user_id == user_id, Roadmap.subject_id == subject_id)
        .order_by(Roadmap.version.desc())
        .all()
    )
