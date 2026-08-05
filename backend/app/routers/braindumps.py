"""BrainDump router (STUDENT-PLANAR G6, phase 36).

Scoped to the current user with single-row-per-user semantics.
GET returns the user's row (or a null-content placeholder if none exists yet).
PUT upserts: updates an existing row or creates a new one.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BrainDump, User
from app.schemas.braindump import BrainDumpCreate, BrainDumpResponse
from app.services.security import get_current_user

router = APIRouter(prefix="/api/braindumps", tags=["braindumps"])


@router.get("/", response_model=dict)
def get_braindump(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the current user's brain dump row.

    If no row exists yet, returns ``{"content": None}`` with 200.
    """
    row = db.query(BrainDump).filter(BrainDump.user_id == current_user.id).first()
    if row is None:
        return {"content": None}
    return BrainDumpResponse.model_validate(row).model_dump()


@router.put("/", response_model=BrainDumpResponse)
def upsert_braindump(data: BrainDumpCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upsert the current user's brain dump content.

    If a row already exists for the user, its ``content`` is updated.
    Otherwise a new row is created.  The ``users.user_id`` UNIQUE
    constraint guarantees no IntegrityError on the upsert path.
    """
    row = db.query(BrainDump).filter(BrainDump.user_id == current_user.id).first()
    if row is None:
        row = BrainDump(user_id=current_user.id, content=data.content)
        db.add(row)
    else:
        row.content = data.content
    db.commit()
    db.refresh(row)
    return BrainDumpResponse.model_validate(row)
