"""Idea 95 — context-aware responses.

``build_bundle`` assembles the per-user context bundle: active subject,
upcoming exams/deadlines, recent topics, question history, session length, and
a memory summary. ``save_override`` lets the user pin values (phrase 44);
``context_prompt_block`` renders the bundle as a compact prompt block so
exam-week vs mid-semester answers differ and deadlines shape prioritization
(phrase 43). The bundle is always per-user (phrase 50).

All derived signals are deterministic (no LLM calls).
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    ContextOverride,
    Course,
    Exam,
    KbConcept,
    LearningEvent,
    SubjectProfile,
    Topic,
    UserMemory,
)
from app.services.kb import KbService, utcnow
from app.services.kb.preferences import get_preferences


# --------------------------------------------------------------------------- #
# Override storage (phrase 44)
# --------------------------------------------------------------------------- #


def get_override(db: Session, user_id: int) -> dict:
    row = db.query(ContextOverride).filter(ContextOverride.user_id == user_id).first()
    data = KbService.json_loads(row.data_json) if row else None
    return data or {}


def save_override(db: Session, user_id: int, data: dict) -> dict:
    """Persist user-pinned context fields (active subject)."""
    clean: dict = {}
    if data.get("active_subject_id"):
        try:
            clean["active_subject_id"] = int(data["active_subject_id"])
        except (ValueError, TypeError):
            pass
    if data.get("active_subject_name"):
        clean["active_subject_name"] = str(data["active_subject_name"])[:200]
    row = db.query(ContextOverride).filter(ContextOverride.user_id == user_id).first()
    if row is None:
        row = ContextOverride(user_id=user_id)
        db.add(row)
    row.data_json = KbService.json_dumps(clean)
    row.updated_at = utcnow()
    db.flush()
    return clean


# --------------------------------------------------------------------------- #
# Derivation (phrase 46)
# --------------------------------------------------------------------------- #


def _active_subject(db: Session, user_id: int) -> dict | None:
    """Active subject from the most recent learning event's topic subject.

    Falls back to the most recently confirmed SubjectProfile. Deterministic.
    """
    event = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == user_id, LearningEvent.topic_id.is_not(None))
        .order_by(LearningEvent.created_at.desc(), LearningEvent.id.desc())
        .first()
    )
    if event is not None and event.topic_id:
        topic = db.query(Topic).filter(Topic.id == event.topic_id, Topic.user_id == user_id).first()
        if topic is not None and topic.subject_id:
            return {"subject_id": topic.subject_id, "subject_name": _subject_name(db, user_id, topic.subject_id)}
    profile = (
        db.query(SubjectProfile)
        .filter(SubjectProfile.user_id == user_id, SubjectProfile.status == "confirmed")
        .order_by(SubjectProfile.updated_at.desc(), SubjectProfile.id.desc())
        .first()
    )
    if profile is None:
        return None
    sid = profile.curriculum_subject_id
    return {"subject_id": sid, "subject_name": profile.parsed_title or f"subject {sid}"} if sid else None


def _subject_name(db: Session, user_id: int, subject_id: int) -> str:
    from app.models import CurriculumSubject

    row = db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()
    return row.name if row else f"subject {subject_id}"


def _upcoming_exams(db: Session, user_id: int, limit: int = 5) -> list[dict]:
    """Upcoming exams for the user's subjects.

    ``Exam.course_id`` points at ``courses.id``; subjects are resolved through
    ``Course.curriculum_subject_id`` (Exam → Course → curriculum subject).
    """
    subject_ids = {
        t.subject_id
        for t in db.query(Topic).filter(Topic.user_id == user_id).all()
        if t.subject_id
    }
    if not subject_ids:
        return []
    exams = (
        db.query(Exam)
        .join(Course, Course.id == Exam.course_id)
        .filter(
            Course.curriculum_subject_id.in_(subject_ids),
            Course.user_id == user_id,
            Exam.date >= date.today(),
        )
        .order_by(Exam.date.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "exam_id": e.id,
            "title": e.title,
            "subject_id": e.course_id,
            "days_until": max(0, (e.date - date.today()).days),
            "date": e.date.isoformat(),
        }
        for e in exams
    ]


def _recent_topics(db: Session, user_id: int, days: int = 14, limit: int = 5) -> list[dict]:
    since = utcnow() - timedelta(days=days)
    topic_ids = [
        e.topic_id
        for e in db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.topic_id.is_not(None),
            LearningEvent.created_at >= since,
        )
        .order_by(LearningEvent.created_at.desc())
        .all()
    ]
    seen: set[int] = set()
    out: list[dict] = []
    for tid in topic_ids:
        if tid in seen:
            continue
        seen.add(tid)
        topic = db.query(Topic).filter(Topic.id == tid, Topic.user_id == user_id).first()
        if topic is None:
            continue
        out.append({"topic_id": topic.id, "topic_name": topic.name, "subject_id": topic.subject_id})
        if len(out) >= limit:
            break
    return out


def _question_history(db: Session, user_id: int, days: int = 7) -> dict:
    since = utcnow() - timedelta(days=days)
    rows = (
        db.query(LearningEvent.event_type, LearningEvent.value)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type.in_(("quiz", "revision")),
            LearningEvent.created_at >= since,
        )
        .all()
    )
    total = len(rows)
    accuracy = [max(0.0, min(1.0, float(v or 0.0))) for _t, v in rows]
    return {
        "attempts_7d": total,
        "avg_accuracy_7d": round(sum(accuracy) / len(accuracy), 3) if accuracy else None,
    }


def _memory_summary(db: Session, user_id: int) -> dict:
    rows = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()
    strong = sum(1 for r in rows if (r.strength or 0.0) >= 0.4)
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).count()
    return {"concepts_known": len(rows), "anchors": strong, "concept_rows": concepts}


# --------------------------------------------------------------------------- #
# Bundle
# --------------------------------------------------------------------------- #


def build_bundle(db: Session, user_id: int) -> dict:
    """Assemble the full context bundle (phrases 42, 46)."""
    override = get_override(db, user_id)
    active = _active_subject(db, user_id)
    # Override wins over derivation when the user pinned a subject.
    if override.get("active_subject_id"):
        active = {
            "subject_id": int(override["active_subject_id"]),
            "subject_name": override.get("active_subject_name")
            or _subject_name(db, user_id, int(override["active_subject_id"])),
        }
    prefs = get_preferences(db, user_id)
    return {
        "active_subject": active,
        "upcoming_exams": _upcoming_exams(db, user_id),
        "recent_topics": _recent_topics(db, user_id),
        "question_history": _question_history(db, user_id),
        "session_length_mins": prefs.get("session_length_mins", 30),
        "memory": _memory_summary(db, user_id),
        "override": override,
    }


def context_prompt_block(bundle: dict | None) -> str:
    """Compact prompt context block (phrase 43); empty when nothing to say."""
    if not bundle:
        return ""
    lines: list[str] = []
    active = bundle.get("active_subject")
    if active and active.get("subject_name"):
        lines.append(f"- active subject: {active['subject_name']}")
    exams = bundle.get("upcoming_exams") or []
    if exams:
        nearest = exams[0]
        lines.append(
            f"- nearest exam: {nearest['title']} in {nearest['days_until']} day(s)"
        )
        if len(exams) > 1:
            lines.append(f"- {len(exams)} more upcoming exam(s)")
    topics = bundle.get("recent_topics") or []
    if topics:
        names = ", ".join(t["topic_name"] for t in topics[:3])
        lines.append(f"- recently studied: {names}")
    qh = bundle.get("question_history") or {}
    if qh.get("attempts_7d"):
        acc = qh.get("avg_accuracy_7d")
        acc_txt = f", avg accuracy {acc:.0%}" if acc is not None else ""
        lines.append(f"- this week: {qh['attempts_7d']} practice attempts{acc_txt}")
    if not lines:
        return ""
    return "Current learner context (shape your answer to this):\n" + "\n".join(lines)


__all__ = ["build_bundle", "save_override", "get_override", "context_prompt_block"]
