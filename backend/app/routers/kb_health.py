"""Knowledge health + gap endpoints (Phase 3, Ideas 27–28)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import health as health_svc
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-health"])


@router.get("/health", response_model=dict)
def kb_health(
    refresh: bool = Query(default=False),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Aggregate knowledge-health signals into a 0–100 score (phrase 67).

    ``refresh=true`` forces recomputation (no cache in this version — the
    computation is cheap and per-user).
    """
    return health_svc.compute_health(db, current_user.id)


@router.get("/gaps", response_model=dict)
def kb_gaps(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """List topic-coverage gaps (Idea 28, phrase 76).

    Built on the Phase-5 stub (``coverage_gaps``) for now; a real subject
    taxonomy feeds this in a later phase.
    """
    gaps = health_svc.coverage_gaps(db, current_user.id)
    threshold = 0.2  # KB_GAP_THRESHOLD default — topics below this are gaps.
    flagged = [g for g in gaps if g["coverage"] < threshold]
    return {
        "items": [
            {
                "topic": g["topic"],
                "coverage": g["coverage"],
                "is_gap": g["coverage"] < threshold,
            }
            for g in gaps
        ],
        "gaps": flagged,
        "threshold": threshold,
        "total": len(gaps),
    }
