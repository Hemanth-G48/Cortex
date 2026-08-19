"""Google OAuth endpoints (connect/callback/status/disconnect)."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db
from app.services import google_oauth

router = APIRouter(prefix="/api/auth/google", tags=["google-auth"])

# Frontend URL for redirect after OAuth callback
FRONTEND_URL = "http://localhost:5173"


@router.get("")
def google_connect(db: Session = Depends(get_db)) -> dict:
    """Start the OAuth flow — returns the Google consent URL (no redirect here
    so the frontend can open it in a new tab and poll /status)."""
    if not google_oauth.is_configured():
        return {"url": None, "error": "Google OAuth not configured — set GOOGLE_CLIENT_ID/SECRET"}
    return {"url": google_oauth.auth_url()}


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Handle OAuth callback and redirect to frontend with result."""
    # Validate CSRF state parameter
    if state and not google_oauth._validate_state(state):
        error = "Invalid or expired state parameter (CSRF protection)"
    if error:
        # Redirect to frontend with error
        redirect_url = f"{FRONTEND_URL}/settings?google_error={error}"
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Auth Error</title></head>
            <body>
                <script>
                    window.opener.postMessage({{ type: 'google-oauth', error: '{error}' }}, '{FRONTEND_URL}');
                    window.close();
                </script>
                <p>Authentication failed: {error}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """,
            status_code=200,
        )

    if error:
        # Google returned an error (e.g., redirect_uri_mismatch, access_denied)
        error_desc = request.query_params.get("error_description", error)
        logger.warning("Google OAuth error: %s - %s", error, error_desc)
        redirect_url = f"{FRONTEND_URL}/settings?google_error={error_desc}"
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Auth Error</title></head>
            <body>
                <script>
                    window.opener.postMessage({{ type: 'google-oauth', error: '{error_desc}' }}, '{FRONTEND_URL}');
                    window.close();
                </script>
                <p>Authentication failed: {error_desc}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """,
            status_code=200,
        )

    if not code:
        # Log all query params for debugging
        params = dict(request.query_params)
        logger.warning("Missing authorization code. Query params: %s", params)
        # Check if this is a redirect_uri_mismatch (Google sends error in different way)
        if "error" in params:
            error_msg = params.get("error_description", params["error"])
            redirect_url = f"{FRONTEND_URL}/settings?google_error={error_msg}"
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head><title>Google Auth Error</title></head>
                <body>
                    <script>
                        window.opener.postMessage({{ type: 'google-oauth', error: '{error_msg}' }}, '{FRONTEND_URL}');
                        window.close();
                    </script>
                    <p>Authentication failed: {error_msg}</p>
                    <p>You can close this window.</p>
                </body>
                </html>
                """,
                status_code=200,
            )
        raise HTTPException(400, f"Missing authorization code. Received params: {list(params.keys())}")

    try:
        result = google_oauth.exchange_code(code, db)
        email = result.get("email", "")
        # Redirect to frontend with success
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Auth Success</title></head>
            <body>
                <script>
                    window.opener.postMessage({{ type: 'google-oauth', connected: true, email: '{email}' }}, '{FRONTEND_URL}');
                    window.close();
                </script>
                <p>Successfully connected to Google!</p>
                <p>Email: {email}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """,
            status_code=200,
        )
    except Exception as exc:  # noqa: BLE001
        # Redirect to frontend with error
        error_msg = str(exc).replace("'", "\\'")
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Google Auth Error</title></head>
            <body>
                <script>
                    window.opener.postMessage({{ type: 'google-oauth', error: 'Token exchange failed: {error_msg}' }}, '{FRONTEND_URL}');
                    window.close();
                </script>
                <p>Token exchange failed: {error_msg}</p>
                <p>You can close this window.</p>
            </body>
            </html>
            """,
            status_code=200,
        )


@router.get("/status")
def google_status(db: Session = Depends(get_db)) -> dict:
    return google_oauth.status(db)


@router.post("/disconnect")
def google_disconnect(db: Session = Depends(get_db)) -> dict:
    google_oauth.clear_token(db)
    return {"connected": False}
