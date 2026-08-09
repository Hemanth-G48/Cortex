"""Phase 6 "what should I study right now" engine (Idea 59), extended in
Phase 8 (Idea 75) to cross-subject scope.

Scores every confirmed/pending topic on readiness (prerequisites mastered),
weakness (low mastery), due reviews, concept gaps (Group 2), exam proximity, and
subject coverage. Blocked topics (an unmastered prerequisite) are never
recommended — the missing prerequisite is offered instead (phrase 84). The
weights live in ``settings.kb_recommend_weights`` (phrase 43) and the user's
preferred session length shapes the suggested duration (phrase 50).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Exam, Topic, TopicDependency
from app.services.kb.gaps import _topic_concept_index, concept_gaps
from app.services.kb.mastery import mastery_by_topic
from app.services.kb.preferences import get_preferences
from app.services.kb.revision import due_reviews

# Concept-gap scores above this saturate the normalized gap factor at 1.0.
GAP_NORM_DENOM = 0.5
# A topic counts as subject "coverage" above this mastery score.
COVERAGE_SCORE = 0.5


def _prereqs(db: Session, user_id: int, topic_id: int) -> list[int]:
    return [
        d.prereq_topic_id
        for d in db.query(TopicDependency)
        .filter(
            TopicDependency.user_id == user_id,
            TopicDependency.postreq_topic_id == topic_id,
        )
        .all()
    ]


def _is_ready(mastery: dict[int, dict], prereq_ids: list[int]) -> bool:
    """Ready when every prerequisite is at least medium (score ≥ 0.4)."""
    for pid in prereq_ids:
        if mastery.get(pid, {}).get("score", 0.0) < 0.4:
            return False
    return True


def _gap_scores(db: Session, user_id: int) -> dict[int, float]:
    """topic_id -> best concept-gap score (0 when the topic has no gap)."""
    gaps = {g["concept_id"]: g for g in concept_gaps(db, user_id, limit=100)}
    if not gaps:
        return {}
    out: dict[int, float] = {}
    for tid, concept_ids in _topic_concept_index(db, user_id).items():
        scores = [gaps[c]["score"] for c in concept_ids if c in gaps]
        if scores:
            out[tid] = max(scores)
    return out


def _subject_coverage(mastery: dict[int, dict], topics: list[Topic]) -> dict[int, float]:
    """subject_id -> fraction of its topics at/above the coverage bar."""
    total: dict[int, int] = {}
    covered: dict[int, int] = {}
    for t in topics:
        total[t.subject_id] = total.get(t.subject_id, 0) + 1
        m = mastery.get(t.id, {})
        if m.get("classification") == "strong" or m.get("score", 0.0) >= COVERAGE_SCORE:
            covered[t.subject_id] = covered.get(t.subject_id, 0) + 1
    return {sid: covered.get(sid, 0) / total for sid, total in total.items()}


def _exam_days(db: Session, subject_ids: set[int]) -> dict[int, int]:
    """subject_id -> days until the nearest upcoming exam (excluded when none)."""
    out: dict[int, int] = {}
    for subject_id in subject_ids:
        exams = (
            db.query(Exam)
            .filter(Exam.course_id == subject_id, Exam.date >= date.today())
            .order_by(Exam.date.asc())
            .all()
        )
        if exams:
            out[subject_id] = max(1, (exams[0].date - date.today()).days)
    return out


def recommend(
    db: Session,
    user_id: int,
    subject_ids: list[int] | None = None,
    *,
    limit: int = 3,
) -> list[dict]:
    """Top cross-subject recommendations with explainable reasons (phrase 45)."""
    q = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.status.in_(("pending", "confirmed")),
    )
    if subject_ids:
        q = q.filter(Topic.subject_id.in_(subject_ids))
    topics = q.all()
    if not topics:
        return []

    topic_ids = [t.id for t in topics]
    mastery = mastery_by_topic(db, user_id, topic_ids)
    due = {d["topic_id"] for d in due_reviews(db, user_id, on=date.today())}
    weights = settings.kb_recommend_weights
    gap_scores = _gap_scores(db, user_id)
    coverage = _subject_coverage(mastery, topics)
    exam_days = _exam_days(db, {t.subject_id for t in topics})
    session_mins = get_preferences(db, user_id).get("session_length_mins", 30)

    candidates: list[dict] = []
    for t in topics:
        prereq_ids = _prereqs(db, user_id, t.id)
        ready = _is_ready(mastery, prereq_ids)
        m = mastery.get(t.id, {}).get("score", 0.0)
        readiness = 1.0 if ready else 0.0
        weakness = 1.0 - m
        due_score = 1.0 if t.id in due else 0.0
        gap_norm = min(1.0, gap_scores.get(t.id, 0.0) / GAP_NORM_DENOM)
        days = exam_days.get(t.subject_id)
        proximity = 1.0 if days is None else max(0.0, 1.0 - days / 30.0)
        coverage_factor = 1.0 - coverage.get(t.subject_id, 0.0)
        score = (
            readiness * weights.get("readiness", 0.25)
            + weakness * weights.get("weakness", 0.2)
            + due_score * weights.get("due_reviews", 0.15)
            + gap_norm * weights.get("concept_gaps", 0.2)
            + proximity * weights.get("exam_proximity", 0.1)
            + coverage_factor * weights.get("subject_coverage", 0.1)
        )
        candidates.append(
            {
                "topic_id": t.id,
                "topic_name": t.name,
                "subject_id": t.subject_id,
                "score": round(score, 4),
                "ready": ready,
                "blocked_by": [pid for pid in prereq_ids if not _is_ready(mastery, [pid])],
                "session_length_mins": session_mins,
                "reasons": {
                    "readiness": round(readiness, 2),
                    "weakness": round(weakness, 2),
                    "due_reviews": round(due_score, 2),
                    "concept_gaps": round(gap_norm, 2),
                    "exam_proximity": round(proximity, 2),
                    "subject_coverage": round(coverage_factor, 2),
                },
            }
        )

    # Blocked topics sink to the bottom; only ready topics are recommended
    # unless nothing at all is ready (then the first unready is a fallback hint).
    ready_items = [c for c in candidates if c["ready"]]
    pool = ready_items or candidates
    pool.sort(key=lambda c: c["score"], reverse=True)
    return pool[:limit]
