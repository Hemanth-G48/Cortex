"""Google OAuth2 service (99-phase plan, Group 14).

Read-only Classroom/Gmail/Calendar flow implemented with plain httpx REST
(mirrors Shiori-v1's ``server/services/google.js`` shape without the
``googleapis`` SDK). Tokens are stored in the local ``google_tokens`` table
(single-user → one row) and refreshed lazily.
"""
from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import GoogleToken

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
]

# In-memory state store for CSRF protection (single-user app)
_oauth_states: dict[str, float] = {}
_STATE_TTL_SECONDS = 600  # 10 minutes


def _generate_state() -> str:
    """Generate a random state parameter for CSRF protection."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    return state


def _validate_state(state: str) -> bool:
    """Validate and consume a state parameter."""
    if state not in _oauth_states:
        return False
    created = _oauth_states.pop(state)
    return (time.time() - created) < _STATE_TTL_SECONDS


def is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def auth_url() -> str:
    state = _generate_state()
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _save_tokens(db: Session, token_data: dict, email: str | None = None) -> GoogleToken:
    row = db.query(GoogleToken).filter(GoogleToken.id == 1).first()
    if not row:
        row = GoogleToken(id=1)
        db.add(row)
    row.access_token = token_data.get("access_token", "")
    row.refresh_token = token_data.get("refresh_token") or row.refresh_token
    row.token_type = token_data.get("token_type", "Bearer")
    row.expires_in = int(token_data.get("expires_in", 3600))
    row.acquired_at = datetime.now()
    row.scope = token_data.get("scope", "")
    if email:
        row.email = email
    db.commit()
    db.refresh(row)
    return row


def exchange_code(code: str, db: Session) -> dict:
    """Swap the callback code for tokens (Phase 84)."""
    if not is_configured():
        return {"error": "Google OAuth not configured"}
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    token_data = resp.json()
    email = None
    try:
        access = token_data.get("access_token")
        if access:
            user = httpx.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access}"},
                timeout=15.0,
            ).json()
            email = user.get("email")
    except Exception:  # noqa: BLE001 — userinfo is best-effort
        logger.warning("Could not fetch Google userinfo")
    _save_tokens(db, token_data, email)
    return {"connected": True, "email": email}


def _refresh(db: Session, row: GoogleToken) -> GoogleToken | None:
    if not row.refresh_token or not is_configured():
        return None
    try:
        resp = httpx.post(
            TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": row.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return _save_tokens(db, data, row.email)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google token refresh failed: %s", exc)
        return None


def access_token(db: Session) -> str | None:
    """Return a valid access token, refreshing when near expiry."""
    row = db.query(GoogleToken).filter(GoogleToken.id == 1).first()
    if not row or not row.access_token:
        return None
    if not is_configured():
        return None
    acquired = row.acquired_at.timestamp() if row.acquired_at else 0
    if time.time() - acquired > (row.expires_in or 3600) - 60:
        refreshed = _refresh(db, row)
        if not refreshed:
            return None
        return refreshed.access_token
    return row.access_token


def clear_token(db: Session) -> None:
    row = db.query(GoogleToken).filter(GoogleToken.id == 1).first()
    if row:
        db.delete(row)
        db.commit()


def status(db: Session) -> dict:
    row = db.query(GoogleToken).filter(GoogleToken.id == 1).first()
    connected = bool(row and row.access_token and access_token(db))
    return {"connected": connected, "email": row.email if row else None, "configured": is_configured()}


def authorized_get(url: str, db: Session, params: dict | None = None, headers: dict | None = None) -> dict | list | None:
    """GET a Google API endpoint with the stored token. Returns None when unauthenticated or when the API returns an error."""
    token = access_token(db)
    if not token:
        return None
    try:
        resp = httpx.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}", **(headers or {})},
            timeout=30.0,
        )
        # Return None for auth errors or API errors (401, 403, etc.)
        if resp.status_code in (401, 403, 404):
            logger.warning("Google API returned %d for %s: %s", resp.status_code, url, resp.text[:200])
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Google API HTTP error for %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.warning("Google API request failed for %s: %s", url, exc)
        return None
