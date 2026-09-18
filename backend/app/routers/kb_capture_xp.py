"""Capture-XP endpoint (defect #79 fix).

``POST /api/kb/capture-xp`` — award Second Brain XP for quest/mission
completion and other capture triggers, so the vault-side wallet grows
alongside the quest-centre wallet.

The amount is read from ``settings.kb_xp_rewards`` keyed by ``kind``;
the ``capture_xp_grants`` unique constraint prevents double-counting
per (user, kind, trigger_key).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.kb import KbCaptureXpRequest, KbCaptureXpResponse
from app.services.kb.capture_xp import award_capture_xp
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-capture-xp"])


@router.post("/capture-xp", response_model=KbCaptureXpResponse)
def post_capture_xp(
    body: KbCaptureXpRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbCaptureXpResponse:
    """Award KB capture XP for a named trigger.

    Body: ``{amount, kind?, trigger_key?}``. ``amount`` is the XP to
    attempt; the backend clamps it to ``settings.kb_xp_rewards[kind]``
    when a kind is supplied, otherwise passes ``amount`` through directly.
    """
    kind = body.kind or "custom"
    trigger_key = body.trigger_key or f"custom:{body.amount}"
    amount = body.amount

    granted = award_capture_xp(db, current_user, kind, trigger_key)
    db.commit()
    return KbCaptureXpResponse(xp_awarded=granted)
