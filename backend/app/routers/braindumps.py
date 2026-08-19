"""BrainDump router (STUDENT-PLANAR G6, phase 36; Phase 4 Idea 40).

Scoped to the current user with single-row-per-user semantics.
GET returns the user's row (or a null-content placeholder if none exists yet).
PUT upserts: updates an existing row or creates a new one — and, since Phase 4
(Idea 40), also upserts a draft ``KbDocument`` (status=draft) so captures can
be filed/split from the widget. The widget UX is unchanged (phrase 96).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BrainDump, User
from app.schemas.braindump import BrainDumpCreate, BrainDumpResponse
from app.services.kb import braindump_draft
from app.services.users import current_user

router = APIRouter(prefix="/api/braindumps", tags=["braindumps"])


def _linked_document_id(db: Session, user_id: int) -> int | None:
    """The draft KbDocument this dump upserts, if any (phrase 93)."""
    draft = braindump_draft.find_draft(db, user_id)
    return draft.id if draft else None


@router.get("/", response_model=dict)
def get_braindump(current_user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Return the current user's brain dump row.

    If no row exists yet, returns ``{"content": None}`` with 200.
    """
    row = db.query(BrainDump).filter(BrainDump.user_id == current_user.id).first()
    if row is None:
        return {"content": None, "linked_document_id": _linked_document_id(db, current_user.id)}
    data = BrainDumpResponse.model_validate(row).model_dump()
    data["linked_document_id"] = _linked_document_id(db, current_user.id)
    return data


@router.put("/", response_model=BrainDumpResponse)
def upsert_braindump(data: BrainDumpCreate, current_user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Upsert the current user's brain dump content.

    If a row already exists for the user, its ``content`` is updated.
    Otherwise a new row is created.  The ``users.user_id`` UNIQUE
    constraint guarantees no IntegrityError on the upsert path.

    Phase 4 (Idea 40): the save also upserts a draft ``KbDocument`` so the
    capture can be filed as a note. Backward-compatible — empty saves create
    no draft.
    """
    row = db.query(BrainDump).filter(BrainDump.user_id == current_user.id).first()
    if row is None:
        row = BrainDump(user_id=current_user.id, content=data.content)
        db.add(row)
    else:
        row.content = data.content
    db.commit()
    db.refresh(row)

    # Additive draft pipeline (phrase 91) — never breaks the widget.
    try:
        draft = braindump_draft.upsert_draft(db, current_user.id, data.content)
        linked_id = draft.id if draft else None
    except Exception:
        db.rollback()
        linked_id = None

    resp = BrainDumpResponse.model_validate(row).model_dump()
    resp["linked_document_id"] = linked_id
    return resp
