"""Profile router — the single owner's profile (no login/auth).

Replaces the old ``/api/auth/me`` and ``/api/auth/enrollment`` endpoints.
The application is single-user: ``current_user`` always resolves to the
owner, so no request carries credentials.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.user import EnrollmentUpdate, UserResponse, UserUpdate
from app.services.users import current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=dict)
def get_profile(current_user: User = Depends(current_user)):
    return {"user": UserResponse.model_validate(current_user).model_dump(exclude_none=True)}


@router.get("/prefs", response_model=dict)
def get_prefs(current_user: User = Depends(current_user)):
    """Client preferences stored server-side (audit defect #96)."""
    import json

    try:
        prefs = json.loads(current_user.prefs_json or "{}")
    except (ValueError, TypeError):
        prefs = {}
    return {"prefs": prefs}


@router.put("/prefs", response_model=dict)
def update_prefs(body: dict, current_user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Merge client preferences (e.g. AI model choice) into the stored JSON."""
    import json

    try:
        prefs = json.loads(current_user.prefs_json or "{}")
    except (ValueError, TypeError):
        prefs = {}
    if not isinstance(body, dict):
        raise HTTPException(400, "Body must be a JSON object")
    prefs.update(body)
    current_user.prefs_json = json.dumps(prefs)
    db.commit()
    return {"prefs": prefs}


@router.put("", response_model=dict)
def update_profile(
    body: UserUpdate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(current_user, key, val)
    db.commit()
    db.refresh(current_user)
    return {"user": UserResponse.model_validate(current_user).model_dump(exclude_none=True)}


@router.put("/enrollment", response_model=dict)
def update_enrollment(
    body: EnrollmentUpdate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Bind the owner to an institution/program (SyllabusAI enrollment)."""
    from app.models import CurriculumCourse, Institution

    inst = db.query(Institution).filter(Institution.id == body.institution_id).first()
    if inst is None or not inst.is_active:
        raise HTTPException(
            404,
            f"Institution {body.institution_id} not found or not active",
        )

    program = db.query(CurriculumCourse).filter(
        CurriculumCourse.id == body.program_id,
        CurriculumCourse.institution_id == body.institution_id,
        CurriculumCourse.is_active == True,  # noqa: E712
    ).first()
    if program is None:
        raise HTTPException(
            404,
            f"Program {body.program_id} not found, not active, or does not belong "
            f"to institution {body.institution_id}",
        )

    current_user.institution_id = body.institution_id
    current_user.program_id = body.program_id
    db.commit()
    db.refresh(current_user)
    return {"user": UserResponse.model_validate(current_user).model_dump(exclude_none=True)}
