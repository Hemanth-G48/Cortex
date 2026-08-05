"""Google Calendar sync (events → local Event table, idempotent by google_id)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, User
from app.services import google_oauth

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


@router.get("/events")
def calendar_events(db: Session = Depends(get_db)) -> list[dict]:
    params = {
        "timeMin": datetime.now().isoformat() + "Z",
        "timeMax": (datetime.now() + timedelta(days=30)).isoformat() + "Z",
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 100,
    }
    data = google_oauth.authorized_get(CALENDAR_URL, db, params=params)
    if data is None:
        return _mock_events()

    formatted: list[dict] = []
    user = db.query(User).first()
    for ev in data.get("items", []):
        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
        title = ev.get("summary", "No title")
        formatted.append({
            "id": ev["id"],
            "title": title,
            "start": start,
            "end": (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date"),
            "location": ev.get("location"),
            "link": ev.get("htmlLink"),
        })
        # Idempotent merge into the local Event table (date-based).
        existing = db.query(Event).filter(Event.google_id == ev["id"]).first()
        if existing or not start or not user:
            continue
        try:
            d = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            try:
                d = date.fromisoformat(start[:10])
            except ValueError:
                continue
        db.add(Event(
            user_id=user.id,
            title=title,
            date=d.date() if hasattr(d, "date") else d,
            time=d.time() if hasattr(d, "time") else None,
            location=ev.get("location"),
            google_id=ev["id"],
        ))
    db.commit()
    return formatted


def _mock_events() -> list[dict]:
    now = datetime.now()
    day = timedelta(days=1)
    return [
        {"id": "cal-1", "title": "Biology 101", "start": (now + 2 * day).isoformat(), "end": (now + 2 * day).isoformat(), "location": "Lab 201", "link": "https://calendar.google.com"},
        {"id": "cal-2", "title": "Study: Chemistry", "start": (now + day).isoformat(), "end": (now + day).isoformat(), "location": None, "link": "https://calendar.google.com"},
        {"id": "cal-3", "title": "Math Homework Due", "start": (now + 3 * day).isoformat(), "end": (now + 3 * day).isoformat(), "location": None, "link": "https://calendar.google.com"},
    ]
