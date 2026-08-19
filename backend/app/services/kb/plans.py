"""Phase 6 personalized study plans + exam prep (Ideas 51, 53).

``generate_study_plan`` builds a topic-grounded, availability-constrained plan
from the Phase 5 roadmap (or the topic DAG when no roadmap exists). It is LLM-
assisted (budget-capped) but fully deterministic in fallback: topological order
→ equal weekly split. ``generate_exam_prep`` reverse-schedules from the exam
date with grading-scheme weights, weak-topic priority, and daily task
materialization.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import CurriculumUnit, Exam, Roadmap, StudyPlan, SubjectProfile, Task, Topic
from app.services import ai_client, ai_fallback
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.dependencies import topological_order
from app.services.kb.mastery import mastery_by_topic
from app.services.prompts import study_plan_prompt

DEFAULT_HOURS_PER_DAY = 2.0
DEFAULT_WEEKS = 6


def _subject_topics(db: Session, user_id: int, subject_id: int) -> list[Topic]:
    return (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == subject_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )


def _ordered_topics(db: Session, user_id: int, subject_id: int) -> list[Topic]:
    """Topic DAG order, falling back to unit order (deterministic backbone)."""
    topics = _subject_topics(db, user_id, subject_id)
    if not topics:
        return []
    try:
        ordered = topological_order(db, user_id, subject_id, [t.id for t in topics])
        by_id = {t.id: t for t in topics}
        return [by_id[i] for i in ordered if i in by_id]
    except Exception:  # noqa: BLE001 — cycle or missing graph → unit order
        unit_order: dict[int, int] = {}
        for i, u in enumerate(
            db.query(CurriculumUnit)
            .filter(CurriculumUnit.subject_id == subject_id)
            .order_by(CurriculumUnit.unit_number.asc())
            .all(),
            start=1,
        ):
            unit_order[u.id] = i
        return sorted(
            topics,
            key=lambda t: (unit_order.get(t.unit_id or 0, 0), t.id),
        )


def _split_into_weeks(topics: list[Topic], weeks: int) -> list[list[Topic]]:
    """Equal (approx) weekly split preserving order (phrase 6 fallback)."""
    if not topics:
        return []
    weeks = max(1, weeks)
    chunk = max(1, -(-len(topics) // weeks))
    return [topics[i : i + chunk] for i in range(0, len(topics), chunk)]


def _llm_plan(
    db: Session,
    user_id: int,
    subject_name: str,
    topics: list[Topic],
    hours_per_day: float,
    weeks: int,
) -> list[dict] | None:
    """LLM-assisted weekly assignment (phrase 4), budget-capped."""
    if not (ai_client.ai_available() and budget_allows(db, user_id)):
        return None
    names = [t.name for t in topics]
    raw = ai_client.generate_json(
        study_plan_prompt(subject_name, names, hours_per_day, weeks),
        max_tokens=1600,
    )
    if not (isinstance(raw, dict) and isinstance(raw.get("weeks"), list)):
        return None
    out: list[dict] = []
    for w in raw["weeks"]:
        if not isinstance(w, dict):
            continue
        wk = {
            "week": int(w.get("week") or len(out) + 1),
            "topic": str(w.get("topic") or ""),
            "topic_ids": w.get("topic_ids") or [],
            "hours_estimate": w.get("hours_estimate") or round(hours_per_day, 1),
            "tasks": [str(t) for t in (w.get("tasks") or [])],
        }
        if wk["topic"] or wk["topic_ids"]:
            out.append(wk)
    if out:
        record_generation(db, user_id, "plan")
    return out or None


def generate_study_plan(
    db: Session,
    user_id: int,
    profile: SubjectProfile,
    *,
    hours_per_day: float | None = None,
    weeks: int | None = None,
) -> StudyPlan:
    """Create a new topic-grounded study plan (phrases 4–7)."""
    if profile.curriculum_subject_id is None:
        raise ValueError("Profile is not confirmed")
    subject_id = profile.curriculum_subject_id
    hours = float(hours_per_day or DEFAULT_HOURS_PER_DAY)
    weeks = max(1, int(weeks or DEFAULT_WEEKS))

    topics = _ordered_topics(db, user_id, subject_id)
    subject_name = profile.parsed_title or "Study Plan"

    weeks_out = _llm_plan(db, user_id, subject_name, topics, hours, weeks)
    fallback = weeks_out is None
    if weeks_out is None:
        buckets = _split_into_weeks(topics, weeks)
        weeks_out = [
            {
                "week": i + 1,
                "topic": ", ".join(t.name for t in bucket),
                "topic_ids": [t.id for t in bucket],
                "hours_estimate": round(
                    max(0.5, sum(t.first_pass_mins or 0 for t in bucket) / 60.0 * (hours / 2.0)),
                    1,
                ),
                "tasks": [f"Study {t.name}" for t in bucket],
            }
            for i, bucket in enumerate(buckets)
        ]

    plan = StudyPlan(
        user_id=user_id,
        subject=subject_name,
        exam_date=None,
        weeks_json=KbService.json_dumps(weeks_out),
    )
    db.add(plan)
    db.flush()
    plan._fallback = fallback  # type: ignore[attr-defined]
    return plan


# ---------------------------------------------------------------------------
# Exam prep (Idea 53)
# ---------------------------------------------------------------------------


def _exam_for(db: Session, profile: SubjectProfile, exam_id: int | None) -> Exam | None:
    if exam_id is None:
        return None
    exam = db.get(Exam, exam_id)
    return exam


def _exam_date(db: Session, profile: SubjectProfile, exam: Exam | None) -> date:
    if exam is not None:
        return exam.date
    # Fall back to the earliest deadline in the parsed syllabus.
    parsed = KbService.json_loads(profile.parsed_json) or {}
    for unit in parsed.get("units", []):
        for d in unit.get("deadlines", []):
            for token in str(d).split():
                try:
                    return datetime.strptime(token, "%Y-%m-%d").date()
                except ValueError:
                    continue
    return date.today() + timedelta(days=14)


def _topic_weight(topic: Topic, mastery: dict[int, dict]) -> float:
    """Grading-scheme + weakness weight (phrases 22–23).

    Base weight from difficulty (E:1, M:1.5, H:2), scaled by weakness
    (1 − mastery) so the least-mastered topics get the most time.
    """
    diff = {"E": 1.0, "M": 1.5, "H": 2.0}.get(topic.difficulty or "M", 1.0)
    m = mastery.get(topic.id, {}).get("score", 0.0)
    weakness = max(0.3, 1.0 - m)  # floor so strong topics keep some time
    return round(diff * weakness, 3)


def generate_exam_prep(
    db: Session,
    user_id: int,
    profile: SubjectProfile,
    *,
    exam_id: int | None = None,
) -> dict:
    """Reverse-schedule topics from the exam date (phrases 21–27)."""
    if profile.curriculum_subject_id is None:
        raise ValueError("Profile is not confirmed")
    subject_id = profile.curriculum_subject_id
    exam = _exam_for(db, profile, exam_id)
    target = _exam_date(db, profile, exam)
    today = date.today()
    days_left = max(1, (target - today).days)
    if days_left > 365:
        days_left = 365

    topics = _ordered_topics(db, user_id, subject_id)
    mastery = mastery_by_topic(db, user_id, [t.id for t in topics])
    # Hardest/most-weighted first, bucketed into daily slots (phrase 24).
    weighted = sorted(
        topics,
        key=lambda t: _topic_weight(t, mastery),
        reverse=True,
    )
    slots = min(days_left, len(weighted)) if weighted else 0
    buckets: list[list[Topic]] = [[] for _ in range(slots)]
    for i, t in enumerate(weighted):
        buckets[i % slots].append(t)

    daily_tasks: list[dict] = []
    for i, bucket in enumerate(buckets):
        day = target - timedelta(days=slots - i)
        daily_tasks.append(
            {
                "date": day.isoformat(),
                "topic_ids": [t.id for t in bucket],
                "topics": [t.name for t in bucket],
                "est_minutes": sum(t.first_pass_mins or 0 for t in bucket),
            }
        )

    return {
        "exam_id": exam.id if exam else None,
        "exam_title": exam.title if exam else profile.parsed_title,
        "exam_date": target.isoformat(),
        "days_left": days_left,
        "daily_tasks": daily_tasks,
    }


def materialize_exam_tasks(
    db: Session,
    user_id: int,
    profile: SubjectProfile,
    prep: dict,
) -> int:
    """Create a Task per exam-prep day (phrase 25). Idempotent per date."""
    created = 0
    for day in prep["daily_tasks"]:
        d = datetime.strptime(day["date"], "%Y-%m-%d").date()
        title = f"Exam prep ({day['topics'][0] if day['topics'] else 'review'})"
        existing = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.due_date == d,
                Task.title == title,
            )
            .first()
        )
        if existing is not None:
            continue
        db.add(
            Task(
                user_id=user_id,
                title=title,
                due_date=d,
                status="Not started",
                priority_tag="High",
            )
        )
        created += 1
    db.flush()
    return created
