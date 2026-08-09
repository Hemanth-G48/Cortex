"""Phase 8 — Personalization & Learning Memory router (Ideas 71–80).

Exposes the Phase 8 services under user-scoped endpoints:

- ``GET/PUT /api/users/me/preferences`` — learning profile (Idea 71).
- ``POST /api/kb/preferences/nudge`` — implicit style adjustment (phrase 25).
- ``GET /api/kb/gaps/concepts`` — concept-level knowledge gaps (Idea 72).
- ``POST /api/kb/explain/personalized`` — anchored, preference-aware explanation (Idea 73).
- ``GET /api/kb/memory``, ``POST /api/kb/memory/bump``, ``POST /api/kb/memory/decay`` — learning memory (Idea 79).
- ``GET /api/kb/recommend/next`` — single best next action (Idea 75, phrase 44).
- ``GET /api/kb/documents/{id}/connect-suggestions`` + confirm — connect (Idea 76).
- ``GET/POST /api/kb/suggestions/missing-notes`` + accept/dismiss — missing notes (Idea 77).
- ``POST /api/kb/outdated/scan``, review queue, resolve — outdated notes (Idea 78).

Every query filters ``user_id``; every generation is budget-capped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import connect as connect_service
from app.services.kb import explain as explain_service
from app.services.kb import gaps as gaps_service
from app.services.kb import memory as memory_service
from app.services.kb import next_action as next_action_service
from app.services.kb import outdated as outdated_service
from app.services.kb import preferences as preferences_service
from app.services.kb import suggestions as suggestions_service
from app.services.security import get_current_user

router = APIRouter(prefix="/api", tags=["kb-personal"])


# ---------------------------------------------------------------------------
# Idea 71 — learning preference profile
# ---------------------------------------------------------------------------
class PreferencesRequest(BaseModel):
    # Numeric fields deliberately have NO ge/le bounds here: the service
    # (``preferences.upsert_preferences``) clamps them (Idea 71), so an
    # out-of-range client value must be clamped, not rejected with a 422.
    depth: str | None = Field(default=None, max_length=20)
    examples_vs_theory: float | None = None
    style: str | None = Field(default=None, max_length=20)
    session_length_mins: int | None = None
    explanation_style: str | None = Field(default=None, max_length=20)
    onboarding_completed: bool | None = None


@router.get("/users/me/preferences")
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return preferences_service.get_preferences(db, current_user.id)


@router.put("/users/me/preferences")
def update_my_preferences(
    body: PreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = preferences_service.upsert_preferences(
        db, current_user.id, body.model_dump(exclude_none=True)
    )
    db.commit()
    return profile


class NudgeRequest(BaseModel):
    feedback: str = Field(min_length=1, max_length=500)


@router.post("/kb/preferences/nudge")
def nudge_preferences(
    body: NudgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = preferences_service.nudge_for_feedback(db, current_user.id, body.feedback)
    db.commit()
    return result


# ---------------------------------------------------------------------------
# Idea 72 — concept-level knowledge gaps
# ---------------------------------------------------------------------------
@router.get("/kb/gaps/concepts")
def get_concept_gaps(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": gaps_service.concept_gaps(db, current_user.id, limit=limit)}


# ---------------------------------------------------------------------------
# Idea 73 — personalized explanations
# ---------------------------------------------------------------------------
class PersonalizedExplainRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=500)
    depth: str | None = Field(default=None, max_length=20)
    document_ids: list[int] | None = None


@router.post("/kb/explain/personalized")
def explain_personalized(
    body: PersonalizedExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return explain_service.explain_personalized(
        db,
        current_user.id,
        body.concept,
        depth=body.depth,
        document_ids=body.document_ids,
    )


# ---------------------------------------------------------------------------
# Idea 79 — learning memory
# ---------------------------------------------------------------------------
@router.get("/kb/memory")
def get_memory(
    limit: int = Query(default=200, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": memory_service.get_memory(db, current_user.id, limit=limit)}


class MemoryBumpRequest(BaseModel):
    concept_ids: list[int] = Field(min_length=1, max_length=100)
    delta: float = Field(default=0.1, ge=0.0, le=1.0)
    source: str = Field(default="practice", max_length=20)


@router.post("/kb/memory/bump")
def bump_memory(
    body: MemoryBumpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    touched = memory_service.bump(
        db, current_user.id, body.concept_ids, delta=body.delta, source=body.source
    )
    db.commit()
    return {"touched": touched}


@router.post("/kb/memory/decay")
def decay_memory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    touched = memory_service.decay(db, current_user.id)
    db.commit()
    return {"decayed": touched}


# ---------------------------------------------------------------------------
# Idea 75 — recommend next (phrase 44)
# ---------------------------------------------------------------------------
@router.get("/kb/recommend/next")
def recommend_next(
    limit: int = Query(default=1, ge=1, le=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = next_action_service.recommend(db, current_user.id, limit=limit)
    return {"items": items}


# ---------------------------------------------------------------------------
# Idea 76 — connect new documents to existing notes
# ---------------------------------------------------------------------------
@router.get("/kb/documents/{document_id}/connect-suggestions")
def connect_suggestions(
    document_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return connect_service.connect_suggestions(db, current_user.id, document_id, limit=limit)


class ConnectRequest(BaseModel):
    target_document_id: int
    relation: str = Field(default="RELATED", max_length=20)


@router.post("/kb/documents/{document_id}/connect")
def confirm_connect(
    document_id: int,
    body: ConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = connect_service.confirm_connect(
            db, current_user.id, document_id, body.target_document_id, relation=body.relation
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    return result


# ---------------------------------------------------------------------------
# Idea 77 — missing-note suggestions
# ---------------------------------------------------------------------------
@router.get("/kb/suggestions/missing-notes")
def list_missing_notes(
    status: str = Query(default="suggested", pattern="^(suggested|accepted|dismissed)$"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": suggestions_service.list_suggestions(db, current_user.id, status=status, limit=limit)}


@router.post("/kb/suggestions/missing-notes")
def suggest_missing_notes(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = suggestions_service.suggest_missing_notes(db, current_user.id, limit=limit)
    db.commit()
    return {"items": items}


@router.post("/kb/suggestions/{suggestion_id}/accept")
def accept_suggestion(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = suggestions_service.accept_suggestion(db, current_user.id, suggestion_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return result


@router.post("/kb/suggestions/{suggestion_id}/dismiss")
def dismiss_suggestion(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = suggestions_service.dismiss_suggestion(db, current_user.id, suggestion_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return result


# ---------------------------------------------------------------------------
# Idea 78 — outdated-note review queue
# ---------------------------------------------------------------------------
@router.post("/kb/outdated/scan")
def scan_outdated(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = outdated_service.scan(db, current_user.id)
    db.commit()
    return result


@router.get("/kb/outdated/review")
def outdated_review(
    status: str = Query(default="open", pattern="^(open|updated|archived|dismissed)$"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": outdated_service.review_queue(db, current_user.id, status=status, limit=limit)}


class ResolveOutdatedRequest(BaseModel):
    # No regex here: the service validates the action and raises ValueError →
    # 400, so an invalid action surfaces as a 400 (not a Pydantic 422).
    action: str = Field(min_length=1, max_length=20)


@router.post("/kb/outdated/{note_id}/resolve")
def resolve_outdated(
    note_id: int,
    body: ResolveOutdatedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = outdated_service.resolve(db, current_user.id, note_id, body.action)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.commit()
    return result
