"""Google OAuth endpoints (connect/callback/status/disconnect)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import google_oauth

router = APIRouter(prefix="/api/auth/google", tags=["google-auth"])


@router.get("")
def google_connect(db: Session = Depends(get_db)) -> dict:
    """Start the OAuth flow — returns the Google consent URL (no redirect here
    so the frontend can open it in a new tab and poll /status)."""
    if not google_oauth.is_configured():
        return {"url": None, "error": "Google OAuth not configured — set GOOGLE_CLIENT_ID/SECRET"}
    return {"url": google_oauth.auth_url()}


@router.get("/callback")
def google_callback(code: str | None = None, error: str | None = None, db: Session = Depends(get_db)) -> dict:
    if error:
        return {"connected": False, "error": f"Google auth error: {error}"}
    if not code:
        raise HTTPException(400, "Missing authorization code")
    try:
        return google_oauth.exchange_code(code, db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Token exchange failed: {exc}") from exc


@router.get("/status")
def google_status(db: Session = Depends(get_db)) -> dict:
    return google_oauth.status(db)


@router.post("/disconnect")
def google_disconnect(db: Session = Depends(get_db)) -> dict:
    google_oauth.clear_token(db)
    return {"connected": False}
