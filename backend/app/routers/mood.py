"""Mood tracking router (Zenith-Study-Planner G2, Phases 8–14)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MoodLog
from app.schemas.mood import (
    MoodAnalytics,
    MoodCreate,
    MoodInsight,
    MoodResponse,
    MoodWeekly,
    SessionParams,
)
from app.services import mood as mood_service
from app.services.users import current_user_id

router = APIRouter(prefix="/api/mood", tags=["mood"])


@router.post("", response_model=MoodResponse)
def create_mood(data: MoodCreate, db: Session = Depends(get_db)):
    log = MoodLog(
        user_id=current_user_id(db),
        mood=data.mood,
        energy=data.energy,
        note=data.note,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[MoodResponse])
def list_moods(
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(MoodLog).filter(MoodLog.user_id == current_user_id(db))
    if start:
        query = query.filter(MoodLog.logged_at >= datetime.fromisoformat(start))
    if end:
        query = query.filter(MoodLog.logged_at <= datetime.fromisoformat(end))
    return query.order_by(MoodLog.logged_at.desc()).limit(limit).all()


@router.delete("/{mood_id}")
def delete_mood(mood_id: int, db: Session = Depends(get_db)):
    log = db.query(MoodLog).filter(
        MoodLog.id == mood_id, MoodLog.user_id == current_user_id(db)
    ).first()
    if not log:
        raise HTTPException(404, "Mood entry not found")
    db.delete(log)
    db.commit()
    return {"ok": True}


# ── Session design mapping (Phase 10) ───────────────────────────────────── #

@router.get("/session-params", response_model=SessionParams)
def get_session_params(mood: str = Query(default="focused")):
    params = mood_service.session_params(mood)
    return SessionParams(mood=mood.strip().lower(), **params)


# ── Analytics / insights / weekly (Phases 11–13) ────────────────────────── #

@router.get("/analytics", response_model=MoodAnalytics)
def get_analytics(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return mood_service.analytics(db, user_id=current_user_id(db), days=days)


@router.get("/weekly", response_model=MoodWeekly)
def get_weekly(days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return MoodWeekly(days=mood_service.weekly(db, user_id=current_user_id(db), days=days))


@router.get("/insights", response_model=list[MoodInsight])
def get_insights(days: int = Query(default=7, ge=1, le=31), db: Session = Depends(get_db)):
    return mood_service.insights(db, user_id=current_user_id(db), days=days)
