from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, KbSource, Note, Goal, User
from app.schemas.note import NoteCreate, NotePinResponse, NoteResponse, GoalCreate, GoalResponse

router = APIRouter(prefix="/api", tags=["notes"])


# ---------------------------------------------------------------------------
# DB-notes → KB bridge (audit defects #15/#78/#94)
#
# Notes written in the app are mirrored as markdown files inside a dedicated
# KB source ("App Notes") so they show up in vault search, the knowledge graph
# and every other KB surface without a second editing system.
# ---------------------------------------------------------------------------

APP_NOTES_SOURCE_NAME = "App Notes (DB bridge)"
APP_NOTES_REL = "app-notes"


def _app_notes_source(db: Session) -> KbSource | None:
    """The dedicated mirror source, created on first use."""
    src = (
        db.query(KbSource)
        .filter(KbSource.name == APP_NOTES_SOURCE_NAME)
        .first()
    )
    if src is None:
        user = db.query(User).first()
        if user is None:
            return None
        import os

        root = os.path.join("second_brain", "app-notes")
        os.makedirs(root, exist_ok=True)
        src = KbSource(
            user_id=user.id,
            name=APP_NOTES_SOURCE_NAME,
            source_type="vault_folder",
            root_path=root,
            enabled=True,
        )
        db.add(src)
        db.commit()
        db.refresh(src)
    return src


def _mirror_note_to_kb(db: Session, note: Note) -> None:
    """Create/update the KB mirror document for a DB note. Never raises."""
    try:
        from app.services.kb import KbService
        from app.services.kb.auto_sync import _stage
        from app.services.kb.pipeline import ingest_document

        src = _app_notes_source(db)
        if src is None:
            return
        rel_path = f"{APP_NOTES_REL}/{note.id}.md"
        body = f"# {note.title}\n\n{note.content or ''}\n"
        digest = KbService.content_hash(body.encode("utf-8"))

        doc = (
            db.query(KbDocument)
            .filter(
                KbDocument.user_id == src.user_id,
                KbDocument.source_id == src.id,
                KbDocument.path_rel == rel_path,
            )
            .first()
        )
        if doc is not None and doc.content_hash == digest:
            return  # unchanged
        if doc is None:
            doc = KbDocument(
                user_id=src.user_id,
                source_id=src.id,
                path_rel=rel_path,
                title=note.title,
                doc_type="md",
                status="new",
            )
        else:
            doc.content_hash = digest
            doc.status = "changed"
            doc.title = note.title
        doc.content_hash = digest
        doc.file_path = _stage(src, rel_path, body)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        ingest_document(db, doc)
    except Exception:  # noqa: BLE001 — mirroring must never break note CRUD
        db.rollback()


def _remove_note_mirror(db: Session, note_id: int) -> None:
    """Drop the KB mirror document when the DB note is deleted."""
    try:
        doc = (
            db.query(KbDocument)
            .filter(KbDocument.path_rel == f"{APP_NOTES_REL}/{note_id}.md")
            .first()
        )
        if doc is not None:
            db.delete(doc)
            db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


# -- Notes --
@router.get("/notes", response_model=List[NoteResponse])
def list_notes(db: Session = Depends(get_db)):
    return (
        db.query(Note)
        .order_by(Note.pinned.desc(), Note.created_date.desc(), Note.id.desc())
        .all()
    )


@router.get("/courses/{course_id}/notes", response_model=List[NoteResponse])
def list_course_notes(course_id: int, db: Session = Depends(get_db)):
    return db.query(Note).filter(Note.course_id == course_id).order_by(Note.pinned.desc(), Note.id.desc()).all()


@router.post("/notes", response_model=NoteResponse)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["updated_at"] = datetime.now()
    note = Note(**payload)
    db.add(note)
    db.commit()
    db.refresh(note)
    _mirror_note_to_kb(db, note)
    return note


@router.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, data: NoteCreate, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    for key, val in data.model_dump().items():
        setattr(note, key, val)
    note.updated_at = datetime.now()
    db.commit()
    db.refresh(note)
    _mirror_note_to_kb(db, note)
    return note


@router.put("/notes/{note_id}/pin", response_model=NotePinResponse)
def pin_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    note.pinned = not note.pinned
    note.updated_at = datetime.now()
    db.commit()
    return NotePinResponse(id=note.id, pinned=note.pinned)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
    _remove_note_mirror(db, note_id)
    return {"ok": True}


@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    db.delete(goal)
    db.commit()
    return {"ok": True}


# -- Goals --
@router.get("/goals", response_model=List[GoalResponse])
def list_goals(habit_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Goal)
    if habit_id is not None:
        q = q.filter(Goal.habit_id == habit_id)
    return q.all()


@router.post("/goals", response_model=GoalResponse)
def create_goal(data: GoalCreate, db: Session = Depends(get_db)):
    goal = Goal(**data.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.put("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: int, data: GoalCreate, db: Session = Depends(get_db)):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    for key, val in data.model_dump().items():
        setattr(goal, key, val)
    db.commit()
    db.refresh(goal)
    return goal


@router.post("/goals/{goal_id}/complete", response_model=GoalResponse)
def complete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    goal.is_completed = True
    goal.progress_percentage = 100.0
    db.commit()
    db.refresh(goal)
    return goal
