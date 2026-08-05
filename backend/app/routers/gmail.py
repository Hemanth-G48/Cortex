"""Gmail router (unread count + recent messages)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import google_oauth

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

GMAIL_LIST_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


@router.get("/unread")
def gmail_unread(db: Session = Depends(get_db)) -> dict:
    data = google_oauth.authorized_get(GMAIL_LIST_URL, db, params={"maxResults": 1, "q": "is:unread"})
    if data is None:
        return {"count": 3}  # mock fallback
    return {"count": data.get("resultSizeEstimate", 0)}


@router.get("/messages")
def gmail_messages(limit: int = 10, db: Session = Depends(get_db)) -> list[dict]:
    data = google_oauth.authorized_get(
        GMAIL_LIST_URL,
        db,
        params={"maxResults": 20, "q": "from:teacher OR from:professor OR subject:classroom OR subject:assignment"},
    )
    if data is None:
        return _mock_messages()

    messages: list[dict] = []
    for m in (data.get("messages") or [])[:limit]:
        detail = google_oauth.authorized_get(
            f"{GMAIL_LIST_URL}/{m['id']}",
            db,
            params={"format": "metadata", "metadataHeaders": "From,Subject,Date"},
        )
        if not detail:
            continue
        headers = {h["name"].lower(): h["value"] for h in (detail.get("payload") or {}).get("headers", [])}
        messages.append({
            "id": m["id"],
            "from": headers.get("from"),
            "subject": headers.get("subject"),
            "date": headers.get("date"),
            "snippet": detail.get("snippet", ""),
        })
    return messages


def _mock_messages() -> list[dict]:
    return [
        {"id": "m1", "from": "Dr. Smith <drsmith@school.edu>", "subject": "Reminder: Biology Lab Tomorrow", "date": "2026-08-02", "snippet": "Just a reminder about the cell biology lab tomorrow at 2pm..."},
        {"id": "m2", "from": "Google Classroom <noreply@classroom.google.com>", "subject": "New grade posted", "date": "2026-08-02", "snippet": "Your teacher has posted a grade..."},
        {"id": "m3", "from": "Prof. Johnson <pjohnson@school.edu>", "subject": "Office Hours Change", "date": "2026-08-01", "snippet": "Office hours moved to Thursday this week..."},
    ]
