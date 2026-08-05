from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Note, Goal
from app.schemas.note import NoteCreate, NotePinResponse, NoteResponse, GoalCreate, GoalResponse

router = APIRouter(prefix="/api", tags=["notes"])


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
