"""Phase 6 — Study Planning & Execution router (Ideas 51–60).

Endpoints:
- ``POST/GET /api/subjects-ai/{id}/study-plan`` — topic-grounded plan (Idea 51)
- ``POST/GET /api/subjects-ai/{id}/exam-prep`` — reverse schedule (Idea 53)
- ``POST /api/topics/{id}/review`` + ``GET /api/reviews/due`` — SM-2 (Idea 52)
- ``GET /api/subjects-ai/{id}/progress`` — progress dashboard (Idea 57)
- ``GET /api/subjects-ai/weak-topics`` — ranked weak list (Idea 58)
- ``GET /api/subjects-ai/next-action`` — study-now (Idea 59)
- ``POST /api/sessions/...`` — micro-sessions + pomodoro (Idea 60)

Every endpoint is user-scoped via ``get_current_user``.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MicroSession, StudyPlan, SubjectProfile, Topic, User
from app.services.kb import KbService
from app.services.kb import adapt as adapt_service
from app.services.kb import next_action as next_action_service
from app.services.kb import plans as plans_service
from app.services.kb import revision as revision_service
from app.services.kb import sessions as sessions_service
from app.services.kb.mastery import mastery_by_topic, progress_payload
from app.services.security import get_current_user

router = APIRouter(prefix="/api", tags=["kb-study"])


def _profile_or_404(db: Session, user_id: int, profile_id: int) -> SubjectProfile:
    profile = (
        db.query(SubjectProfile)
        .filter(SubjectProfile.id == profile_id, SubjectProfile.user_id == user_id)
        .first()
    )
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return profile


def _confirmed(db: Session, user_id: int, profile: SubjectProfile) -> int:
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    return profile.curriculum_subject_id


def _topic_or_404(db: Session, user_id: int, topic_id: int) -> Topic:
    topic = db.query(Topic).get(topic_id)
    if topic is None or topic.user_id != user_id:
        raise HTTPException(404, "Topic not found")
    return topic


# ---------------------------------------------------------------------------
# Idea 51 — personalized study plan
# ---------------------------------------------------------------------------


class StudyPlanRequest(BaseModel):
    hours_per_day: float | None = Field(default=None, ge=0.25, le=12.0)
    weeks: int | None = Field(default=None, ge=1, le=26)


def _plan_dict(plan: StudyPlan) -> dict:
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "subject": plan.subject,
        "exam_date": plan.exam_date,
        "weeks": KbService.json_loads(plan.weeks_json) or [],
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


@router.post("/subjects-ai/{profile_id}/study-plan")
def generate_study_plan(
    profile_id: int,
    body: StudyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    _confirmed(db, current_user.id, profile)
    try:
        plan = plans_service.generate_study_plan(
            db,
            current_user.id,
            profile,
            hours_per_day=body.hours_per_day,
            weeks=body.weeks,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": _plan_dict(plan)}


@router.get("/subjects-ai/{profile_id}/study-plan")
def get_study_plan(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    _confirmed(db, current_user.id, profile)
    plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.user_id == current_user.id,
            StudyPlan.subject == (profile.parsed_title or ""),
        )
        .order_by(StudyPlan.id.desc())
        .first()
    )
    return {"plan": _plan_dict(plan) if plan else None}


# ---------------------------------------------------------------------------
# Idea 52 — revision scheduling (SM-2)
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    grade: int = Field(ge=0, le=5)


@router.post("/topics/{topic_id}/review")
def review_topic(
    topic_id: int,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = _topic_or_404(db, current_user.id, topic_id)
    schedule = revision_service.apply_review(db, current_user.id, topic, body.grade)
    # Phase 7 (Idea 69, phrase 81): revision-completion XP, once per schedule.
    xp_granted = 0
    if body.grade >= 3:
        from app.services.kb.capture_xp import award_capture_xp

        xp_granted = award_capture_xp(db, current_user, "revision", f"revision:{schedule.id}")
    db.commit()
    return {
        "ok": True,
        "topic_id": topic_id,
        "schedule": revision_service.revision_state(db, current_user.id, topic_id),
        "due_date": schedule.due_date.date().isoformat() if schedule.due_date else None,
        "xp_granted": xp_granted,
    }


@router.get("/reviews/due")
def get_due_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": revision_service.due_reviews(db, current_user.id, on=date.today())}


@router.post("/reviews/materialize")
def materialize_reviews(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    created = revision_service.materialize_due(db, current_user.id, on=date.today())
    db.commit()
    return {"ok": True, "materialized": created}


# ---------------------------------------------------------------------------
# Idea 53 — exam prep
# ---------------------------------------------------------------------------


@router.post("/subjects-ai/{profile_id}/exam-prep")
def generate_exam_prep(
    profile_id: int,
    exam_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    _confirmed(db, current_user.id, profile)
    try:
        prep = plans_service.generate_exam_prep(
            db, current_user.id, profile, exam_id=exam_id
        )
        created = plans_service.materialize_exam_tasks(db, current_user.id, profile, prep)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"prep": prep, "tasks_created": created}


@router.get("/subjects-ai/{profile_id}/exam-prep")
def get_exam_prep(
    profile_id: int,
    exam_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    _confirmed(db, current_user.id, profile)
    try:
        prep = plans_service.generate_exam_prep(
            db, current_user.id, profile, exam_id=exam_id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"prep": prep}


# ---------------------------------------------------------------------------
# Idea 57 — progress + Idea 58 — weak topics
# ---------------------------------------------------------------------------


@router.get("/subjects-ai/{profile_id}/progress")
def subject_progress(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    subject_id = _confirmed(db, current_user.id, profile)
    topic_ids = [
        t.id
        for t in db.query(Topic)
        .filter(Topic.user_id == current_user.id, Topic.subject_id == subject_id)
        .all()
    ]
    return progress_payload(db, current_user.id, topic_ids)


@router.get("/subjects-ai/weak-topics")
def weak_topics(
    subject_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Topic).filter(
        Topic.user_id == current_user.id,
        Topic.status.in_(("pending", "confirmed")),
    )
    if subject_id:
        q = q.filter(Topic.subject_id == subject_id)
    topics = q.all()
    mastery = mastery_by_topic(db, current_user.id, [t.id for t in topics])
    weak = [
        {
            "topic_id": t.id,
            "topic_name": t.name,
            "subject_id": t.subject_id,
            "score": mastery[t.id]["score"],
            "classification": mastery[t.id]["classification"],
            "evidence": mastery[t.id]["evidence"],
        }
        for t in topics
        if mastery[t.id]["classification"] in ("weak", "unknown")
    ]
    weak.sort(key=lambda x: x["score"])
    return {"items": weak[:limit], "total": len(weak)}


# ---------------------------------------------------------------------------
# Idea 59 — next action
# ---------------------------------------------------------------------------


@router.get("/subjects-ai/next-action")
def next_action(
    subject_id: int | None = Query(default=None),
    limit: int = Query(default=3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = next_action_service.recommend(
        db,
        current_user.id,
        [subject_id] if subject_id else None,
        limit=limit,
    )
    return {"items": items}


# ---------------------------------------------------------------------------
# Idea 80 — adaptive learning paths (Phase 8, phrase 94)
# ---------------------------------------------------------------------------


class AdaptRoadmapRequest(BaseModel):
    weekly_budget: int | None = Field(default=None, ge=60, le=6000)
    deadline: date | None = None


@router.post("/subjects-ai/{profile_id}/roadmap/adapt")
def adapt_roadmap(
    profile_id: int,
    body: AdaptRoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recompute the subject roadmap from mastery + due reviews + gaps.

    Returns the new version plus the explainable plan diff
    (``{added_reviews, removed_topics, reordered[], reason}``).
    """
    profile = _profile_or_404(db, current_user.id, profile_id)
    subject_id = _confirmed(db, current_user.id, profile)
    result = adapt_service.adapt_roadmap(
        db,
        current_user.id,
        subject_id,
        weekly_budget=body.weekly_budget,
        deadline=body.deadline,
    )
    db.commit()
    return {"adaptation": result}


# ---------------------------------------------------------------------------
# Idea 60 — micro-sessions
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    topic_id: int
    duration_mins: int | None = Field(default=None, ge=15, le=45)


@router.post("/sessions/start")
def start_session(
    body: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = _topic_or_404(db, current_user.id, body.topic_id)
    session = sessions_service.build_session(
        db, current_user.id, topic, duration_mins=body.duration_mins
    )
    sessions_service.start_session(db, current_user.id, session)
    db.commit()
    return {"session": sessions_service.session_dict(session, topic)}


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(MicroSession).get(session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")
    topic = db.query(Topic).get(session.topic_id) if session.topic_id else None
    sessions_service.complete_session(db, current_user.id, session)
    db.commit()
    return {"ok": True, "session": sessions_service.session_dict(session, topic)}


@router.post("/sessions/{session_id}/pomodoro")
def session_pomodoro(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(MicroSession).get(session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(404, "Session not found")
    pomo = sessions_service.launch_pomodoro(db, current_user.id, session)
    db.commit()
    return {
        "ok": True,
        "pomodoro_id": pomo.id,
        "duration_minutes": pomo.duration_minutes,
        "task_description": pomo.task_description,
    }


@router.get("/sessions/suggested")
def suggested_sessions(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggested micro-sessions from the next-action recommender (phrase 92)."""
    recs = next_action_service.recommend(db, current_user.id, limit=limit)
    out = []
    for rec in recs:
        topic = db.query(Topic).get(rec["topic_id"])
        if topic is None:
            continue
        session = sessions_service.build_session(db, current_user.id, topic)
        out.append(sessions_service.session_dict(session, topic))
    db.flush()
    return {"items": out}
