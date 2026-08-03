from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PomodoroSession
from app.schemas.pomodoro import PomodoroSessionCreate, PomodoroSessionResponse

router = APIRouter(prefix="/api", tags=["pomodoro"])


@router.get("/pomodoro-sessions", response_model=List[PomodoroSessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    return db.query(PomodoroSession).order_by(PomodoroSession.start_time.desc()).all()


@router.post("/pomodoro-sessions", response_model=PomodoroSessionResponse)
def create_session(data: PomodoroSessionCreate, db: Session = Depends(get_db)):
    session = PomodoroSession(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/pomodoro-sessions/{session_id}")
def delete_pomodoro_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(PomodoroSession).filter(PomodoroSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Pomodoro session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}
