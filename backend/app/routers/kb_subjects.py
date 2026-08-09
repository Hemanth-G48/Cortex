"""Phase 5 — Subject Management Core router (Ideas 41–50).

Every endpoint is user-scoped. Review-before-write: proposals are drafts until
``confirm`` writes the existing curriculum tables; topics / unit matches /
dependencies all require explicit user action.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CurriculumUnit, Roadmap, SubjectProfile, Topic, User
from app.services.kb import KbService
from app.services.kb import dependencies as dep_service
from app.services.kb import roadmap as roadmap_service
from app.services.kb import subjects as subjects_service
from app.services.kb import topics as topics_service
from app.services.kb import units as units_service
from app.services.kb.dependencies import DependencyCycleError
from app.services.security import get_current_user

router = APIRouter(prefix="/api/subjects", tags=["kb-subjects"])


# ---------------------------------------------------------------------------
# Proposal lifecycle (Idea 41, phrases 4–7)
# ---------------------------------------------------------------------------


class ImportRequest(BaseModel):
    text: str | None = None
    filename: str | None = None


class ConfirmRequest(BaseModel):
    program_id: int | None = None
    name: str | None = None
    code: str | None = None
    credits: int | None = Field(default=None, ge=0, le=30)


def _profile_or_404(db: Session, user_id: int, profile_id: int) -> SubjectProfile:
    profile = subjects_service.get_profile(db, user_id, profile_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return profile


def _profile_dict(db: Session, profile: SubjectProfile) -> dict:
    parsed = KbService.json_loads(profile.parsed_json) or {}
    topics_count = 0
    units_count = 0
    if profile.curriculum_subject_id:
        from app.models import Topic

        topics_count = (
            db.query(Topic)
            .filter(Topic.user_id == profile.user_id, Topic.subject_id == profile.curriculum_subject_id)
            .count()
        )
        units_count = (
            db.query(CurriculumUnit)
            .filter(CurriculumUnit.subject_id == profile.curriculum_subject_id)
            .count()
        )
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "curriculum_subject_id": profile.curriculum_subject_id,
        "semester": profile.semester,
        "status": profile.status,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "parsed": {
            "title": parsed.get("title"),
            "credits": parsed.get("credits"),
            "grading": parsed.get("grading"),
            "units": parsed.get("units", []),
        },
        "topics_count": topics_count,
        "units_count": units_count,
    }


@router.post("/import")
def import_syllabus(
    body: ImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse syllabus text (or an uploaded file → text) into a proposal."""
    text = (body.text or "").strip()
    if body.filename and not text:
        text = body.filename
    if not text:
        raise HTTPException(400, "Syllabus text is required")
    if len(text) > 200_000:
        raise HTTPException(413, "Syllabus too large (max 200k chars)")
    result = subjects_service.propose(db, current_user.id, text, filename=None)
    db.commit()
    return {
        "profile": _profile_dict(db, result["profile"]),
        "fallback": result["fallback"],
    }


@router.post("/import-file")
async def import_syllabus_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import a syllabus file (PDF/DOCX/MD/TXT) via the text extractor."""
    from app.services.text_extractor import extract

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 10 MB)")
    name = file.filename or "syllabus"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "txt"
    if ext not in ("pdf", "docx", "txt", "md"):
        raise HTTPException(400, "Unsupported file type")
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        text = extract(tmp_path, ext) or ""
    finally:
        import os

        os.unlink(tmp_path)
    if not text.strip():
        raise HTTPException(422, "No text could be extracted from that file")
    result = subjects_service.propose(db, current_user.id, text, filename=name)
    db.commit()
    return {
        "profile": _profile_dict(db, result["profile"]),
        "fallback": result["fallback"],
    }


@router.get("/proposals")
def list_proposals(
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if status and status not in ("proposed", "confirmed", "rejected"):
        raise HTTPException(400, "Invalid status")
    profiles = subjects_service.list_profiles(db, current_user.id, status)
    return {"items": [_profile_dict(db, p) for p in profiles], "total": len(profiles)}


@router.get("")
def list_subjects(
    semester: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subject facet list (Idea 43, phrase 26): filterable by semester."""
    q = db.query(SubjectProfile).filter(SubjectProfile.user_id == current_user.id)
    if semester:
        q = q.filter(SubjectProfile.semester.ilike(f"%{semester}%"))
    if status:
        q = q.filter(SubjectProfile.status == status)
    items = q.order_by(SubjectProfile.created_at.desc()).all()
    return {"items": [_profile_dict(db, p) for p in items], "total": len(items)}


@router.get("/{profile_id}")
def get_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    data = _profile_dict(db, profile)
    data["raw_syllabus_text"] = profile.raw_syllabus_text
    return data


@router.post("/{profile_id}/confirm")
def confirm_proposal(
    profile_id: int,
    body: ConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    try:
        subjects_service.confirm(
            db,
            current_user.id,
            profile,
            program_id=body.program_id,
            name=body.name,
            code=body.code,
            credits=body.credits,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"profile": _profile_dict(db, profile)}


@router.post("/{profile_id}/reject")
def reject_proposal(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    subjects_service.reject(db, current_user.id, profile)
    db.commit()
    return {"ok": True, "profile": _profile_dict(db, profile)}


# ---------------------------------------------------------------------------
# Topics (Idea 44, phrases 36–40)
# ---------------------------------------------------------------------------


@router.post("/{profile_id}/topics/generate")
def generate_topics(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    try:
        created = topics_service.extract_topics(db, current_user.id, profile)
    except ValueError as e:
        raise HTTPException(400, str(e))
    for topic in created:
        topics_service.set_topic_estimates(db, current_user.id, topic)
    db.commit()
    return {"generated": len(created), "fallback": not _ai_used(db, current_user.id, "topics")}


@router.get("/{profile_id}/topics")
def list_topics(
    profile_id: int,
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    q = db.query(Topic).filter(
        Topic.user_id == current_user.id,
        Topic.subject_id == profile.curriculum_subject_id,
    )
    if status:
        q = q.filter(Topic.status == status)
    return {"items": [_topic_dict(t) for t in q.order_by(Topic.id.asc()).all()]}


def _topic_dict(t: Topic) -> dict:
    return {
        "id": t.id,
        "subject_id": t.subject_id,
        "unit_id": t.unit_id,
        "name": t.name,
        "normalized_name": t.normalized_name,
        "bloom_level": t.bloom_level,
        "difficulty": t.difficulty,
        "difficulty_confidence": t.difficulty_confidence,
        "first_pass_mins": t.first_pass_mins,
        "review_mins": t.review_mins,
        "mastery_mins": t.mastery_mins,
        "outcomes": KbService.json_loads(t.outcomes) or [],
        "status": t.status,
    }


def _topic_or_404(db: Session, user_id: int, topic_id: int) -> Topic:
    topic = db.query(Topic).get(topic_id)
    if topic is None or topic.user_id != user_id:
        raise HTTPException(404, "Topic not found")
    return topic


@router.post("/{profile_id}/topics/{topic_id}/confirm")
def confirm_topic(
    profile_id: int, topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _profile_or_404(db, current_user.id, profile_id)
    topic = _topic_or_404(db, current_user.id, topic_id)
    topics_service.confirm_topic(db, current_user.id, topic)
    db.commit()
    return {"ok": True, "topic": _topic_dict(topic)}


@router.post("/{profile_id}/topics/{topic_id}/reject")
def reject_topic(
    profile_id: int, topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _profile_or_404(db, current_user.id, profile_id)
    topic = _topic_or_404(db, current_user.id, topic_id)
    topics_service.reject_topic(db, current_user.id, topic)
    db.commit()
    return {"ok": True, "topic": _topic_dict(topic)}


class MergeRequest(BaseModel):
    into_topic_id: int


@router.post("/{profile_id}/topics/{topic_id}/merge")
def merge_topic(
    profile_id: int, topic_id: int, body: MergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _profile_or_404(db, current_user.id, profile_id)
    topic = _topic_or_404(db, current_user.id, topic_id)
    into = _topic_or_404(db, current_user.id, body.into_topic_id)
    try:
        topics_service.merge_topic(db, current_user.id, topic, into)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Unit matching (Idea 45, phrases 41–50)
# ---------------------------------------------------------------------------


@router.get("/{profile_id}/match-units")
def match_units(
    profile_id: int,
    use_embeddings: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    parsed = KbService.json_loads(profile.parsed_json) or {}
    candidates = units_service.match_candidates(
        db,
        current_user.id,
        profile.curriculum_subject_id,
        parsed.get("units", []),
        use_embeddings=use_embeddings,
    )
    return {"items": candidates}


class MatchConfirmRequest(BaseModel):
    mapping: dict[str, int | None]


@router.post("/{profile_id}/match-units/confirm")
def confirm_unit_match(
    profile_id: int,
    body: MatchConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    parsed = KbService.json_loads(profile.parsed_json) or {}
    clean = {k: v for k, v in body.mapping.items() if v}
    assigned = units_service.confirm_mapping(
        db, current_user.id, profile.curriculum_subject_id, clean, parsed_units=parsed.get("units", [])
    )
    db.commit()
    return {"ok": True, "topics_assigned": assigned}


# ---------------------------------------------------------------------------
# Topic dependency graph (Idea 46, phrases 51–60)
# ---------------------------------------------------------------------------


@router.get("/{profile_id}/dependencies")
def get_dependencies(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    return dep_service.graph_payload(db, current_user.id, profile.curriculum_subject_id)


@router.post("/{profile_id}/dependencies/generate")
def seed_dependencies(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    parsed = KbService.json_loads(profile.parsed_json) or {}
    created = dep_service.seed_dependencies(
        db, current_user.id, profile.curriculum_subject_id, parsed.get("units", [])
    )
    db.commit()
    return {"created": created}


class AddDependencyRequest(BaseModel):
    prereq_topic_id: int
    postreq_topic_id: int


@router.post("/{profile_id}/dependencies")
def add_dependency(
    profile_id: int,
    body: AddDependencyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    try:
        dep_service.add_dependency(
            db, current_user.id, profile.curriculum_subject_id,
            body.prereq_topic_id, body.postreq_topic_id,
        )
    except DependencyCycleError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True}


@router.delete("/dependencies/{dep_id}")
def delete_dependency(
    dep_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        dep_service.remove_dependency(db, current_user.id, dep_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Roadmap (Idea 47, phrases 61–70)
# ---------------------------------------------------------------------------


class RoadmapRequest(BaseModel):
    weekly_budget: int | None = Field(default=None, ge=60, le=6000)
    deadline: date | None = None


@router.post("/{profile_id}/roadmap/generate")
def generate_roadmap(
    profile_id: int,
    body: RoadmapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    roadmap = roadmap_service.generate_roadmap(
        db, current_user.id, profile.curriculum_subject_id,
        weekly_budget=body.weekly_budget,
        deadline=body.deadline,
    )
    db.commit()
    return {"roadmap": _roadmap_dict(roadmap)}


@router.get("/{profile_id}/roadmap")
def get_roadmap(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    roadmap = roadmap_service.get_active(db, current_user.id, profile.curriculum_subject_id)
    if roadmap is None:
        return {"roadmap": None}
    return {"roadmap": _roadmap_dict(roadmap)}


def _roadmap_dict(r: Roadmap) -> dict:
    return {
        "id": r.id,
        "subject_id": r.subject_id,
        "version": r.version,
        "status": r.status,
        "plan": KbService.json_loads(r.plan_json) or {"weeks": []},
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ---------------------------------------------------------------------------
# Difficulty + time estimates (Ideas 48–49, phrases 71–90)
# ---------------------------------------------------------------------------


class TopicPatchRequest(BaseModel):
    difficulty: str | None = Field(default=None, pattern="^[EMH]$")
    first_pass_mins: int | None = Field(default=None, ge=0, le=6000)
    review_mins: int | None = Field(default=None, ge=0, le=6000)
    mastery_mins: int | None = Field(default=None, ge=0, le=6000)


@router.patch("/topics/{topic_id}")
def patch_topic(
    topic_id: int,
    body: TopicPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manual difficulty / time override (phrases 77, 88)."""
    topic = _topic_or_404(db, current_user.id, topic_id)
    if body.difficulty is not None:
        topic.difficulty = body.difficulty
        topic.difficulty_confidence = 1.0  # manual override is authoritative
    if body.first_pass_mins is not None:
        topic.first_pass_mins = body.first_pass_mins
    if body.review_mins is not None:
        topic.review_mins = body.review_mins
    if body.mastery_mins is not None:
        topic.mastery_mins = body.mastery_mins
    db.commit()
    return {"ok": True, "topic": _topic_dict(topic)}


@router.post("/topics/{topic_id}/recompute")
def recompute_topic(topic_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topic = _topic_or_404(db, current_user.id, topic_id)
    topics_service.set_topic_estimates(db, current_user.id, topic)
    db.commit()
    return {"ok": True, "topic": _topic_dict(topic)}


@router.get("/{profile_id}/time-budget")
def time_budget(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-topic estimates + weekly totals for the roadmap engine/UI (phrase 86)."""
    profile = _profile_or_404(db, current_user.id, profile_id)
    if profile.curriculum_subject_id is None:
        raise HTTPException(400, "Profile is not confirmed yet")
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == current_user.id, Topic.subject_id == profile.curriculum_subject_id)
        .all()
    )
    user = db.query(User).get(current_user.id)
    multiplier = float(user.pacing_multiplier or 1.0) if user else 1.0
    items = [_topic_dict(t) for t in topics]
    weekly = sum(t.first_pass_mins or 0 for t in topics)
    return {
        "items": items,
        "pacing_multiplier": multiplier,
        "total_first_pass_mins": weekly,
        "total_mins": sum((t.first_pass_mins or 0) + (t.review_mins or 0) + (t.mastery_mins or 0) for t in topics),
    }


class PacingRequest(BaseModel):
    multiplier: float = Field(default=1.0, ge=0.1, le=5.0)


@router.put("/me/pacing")
def set_pacing(
    body: PacingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-user pacing multiplier for time estimates (phrase 84)."""
    user = db.query(User).get(current_user.id)
    user.pacing_multiplier = round(body.multiplier, 2)
    db.commit()
    return {"ok": True, "pacing_multiplier": user.pacing_multiplier}


# ---------------------------------------------------------------------------
# Learning outcomes (Idea 50, phrases 91–99)
# ---------------------------------------------------------------------------


@router.get("/topics/{topic_id}/outcomes")
def get_outcomes(topic_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topic = _topic_or_404(db, current_user.id, topic_id)
    return {"topic_id": topic.id, "outcomes": topics_service.get_outcomes(topic)}


class AddOutcomeRequest(BaseModel):
    text: str = Field(min_length=2, max_length=300)


@router.post("/topics/{topic_id}/outcomes")
def add_outcome(
    topic_id: int, body: AddOutcomeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = _topic_or_404(db, current_user.id, topic_id)
    topics_service.add_outcome(db, topic, body.text)
    db.commit()
    return {"ok": True, "outcomes": topics_service.get_outcomes(topic)}


@router.post("/topics/{topic_id}/outcomes/expand")
def expand_outcomes(topic_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topic = _topic_or_404(db, current_user.id, topic_id)
    topics_service.expand_outcomes(db, current_user.id, topic)
    db.commit()
    return {"ok": True, "outcomes": topics_service.get_outcomes(topic)}


@router.post("/topics/{topic_id}/outcomes/{index}/complete")
def complete_outcome(
    topic_id: int, index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = _topic_or_404(db, current_user.id, topic_id)
    try:
        topics_service.complete_outcome(db, current_user.id, topic, index)
    except IndexError:
        raise HTTPException(404, "Outcome not found")
    db.commit()
    return {"ok": True, "outcomes": topics_service.get_outcomes(topic)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ai_used(db: Session, user_id: int, kind: str) -> bool:
    """Best-effort: whether a real LLM call happened for this generation."""
    from app.services.kb.budget import generation_budget

    return generation_budget(db, user_id)["today"] > 0
