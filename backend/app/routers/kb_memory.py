"""Idea 92 — long-term memory router.

- ``GET /api/kb/memory/timeline`` — read-only timeline: episodes + durable facts
  (phrase 19). Note: ``GET /api/kb/memory`` is owned by Phase 8 (Idea 79)
  learning-memory rows, so the Phase 10 timeline lives under ``/timeline``.
- ``POST /api/kb/memory/consolidate`` — run the weekly consolidation job on
  demand (phrase 14).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EpisodicMemory, User
from app.services.kb import KbService
from app.services.kb import memory_longterm as memory_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-memory"])


@router.get("/memory/timeline")
def memory_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    episodes = (
        db.query(EpisodicMemory)
        .filter(EpisodicMemory.user_id == current_user.id)
        .order_by(EpisodicMemory.created_at.desc(), EpisodicMemory.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "episodes": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "summary": e.summary,
                "refs": KbService.json_loads(e.refs),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in episodes
        ],
        "durable_facts": memory_service.durable_facts(db, current_user.id),
        "total": len(episodes),
    }


@router.post("/memory/consolidate")
def run_consolidation(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not KbService.bool_setting("KB_MEMORY_CONSOLIDATION_ENABLED", False):
        raise HTTPException(400, "KB_MEMORY_CONSOLIDATION_ENABLED is disabled")
    result = memory_service.run(db, current_user.id)
    db.commit()
    return result
