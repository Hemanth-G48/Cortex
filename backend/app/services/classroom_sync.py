"""Google Classroom sync (idempotent merge into Course/Assignment).

The response is labelled with ``source`` so the UI can distinguish live data
from the deterministic offline mock: ``{"courses": [...], "source": "live"}``
or ``{"courses": [...], "source": "mock"}``. Mocks are never persisted.

``sync_classroom_courses`` / ``sync_classroom_assignments`` are shared by the
classroom router (thin wrapper) and the course-level Resync action, so a
resync and the standalone sync always behave identically.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Assignment, Course
from app.services import google_oauth

CLASSROOM_COURSES_URL = "https://classroom.googleapis.com/v1/courses"
CLASSROOM_WORK_URL = "https://classroom.googleapis.com/v1/courses/{cid}/courseWork"


def _scoped_course(db: Session, user_id: int, google_id: str) -> Course | None:
    return (
        db.query(Course)
        .filter(Course.user_id == user_id, Course.google_id == google_id)
        .first()
    )


def sync_classroom_courses(db: Session, user_id: int) -> dict:
    """Fetch Classroom courses; merge into the current user's Course rows.

    Returns ``{"courses": [...], "source": "live"}`` or the labelled offline
    mock payload when Google is not connected / the API is not enabled.
    """
    data = google_oauth.authorized_get(
        CLASSROOM_COURSES_URL, db, params={"pageSize": 100, "courseStates": "ACTIVE"}
    )
    if data is None:
        # Connected but the Classroom API may not be enabled in the console.
        from app.models import GoogleToken

        token_row = db.query(GoogleToken).filter(GoogleToken.id == 1).first()
        if token_row and token_row.access_token:
            return {
                "courses": _mock_courses(),
                "source": "mock",
                "warning": "Google Classroom API may not be enabled. Please enable it in Google Cloud Console.",
                "scopes_needed": [
                    "https://www.googleapis.com/auth/classroom.courses.readonly",
                    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
                ],
                "api_console_url": "https://console.cloud.google.com/apis/library/classroom.googleapis.com",
            }
        return {"courses": _mock_courses(), "source": "mock"}  # not connected → labelled mock

    formatted: list[dict] = []
    for c in data.get("courses", []):
        formatted.append(
            {
                "id": c["id"],
                "name": c.get("name"),
                "description": c.get("descriptionHeading") or c.get("description"),
            }
        )
        # Idempotent merge (matched by google id + owner, preserves manual edits).
        existing = _scoped_course(db, user_id, c["id"])
        if existing:
            existing.title = c.get("name") or existing.title
            existing.source_type = "classroom"
            existing.classroom_url = c.get("alternateLink") or existing.classroom_url
        else:
            db.add(
                Course(
                    title=c.get("name") or "Google Classroom Course",
                    status="In progress",
                    google_id=c["id"],
                    user_id=user_id,
                    source_type="classroom",
                    classroom_url=c.get("alternateLink"),
                )
            )
    db.commit()
    return {"courses": formatted, "source": "live"}


def sync_classroom_assignments(db: Session, user_id: int) -> dict:
    """Fetch course work across all courses; merge into Assignment by google_id."""
    courses_data = google_oauth.authorized_get(
        CLASSROOM_COURSES_URL, db, params={"pageSize": 100, "courseStates": "ACTIVE"}
    )
    if courses_data is None:
        return {"assignments": _mock_assignments(), "source": "mock"}

    all_assignments: list[dict] = []
    for c in courses_data.get("courses", []):
        local = _scoped_course(db, user_id, c["id"])
        work = google_oauth.authorized_get(
            CLASSROOM_WORK_URL.format(cid=c["id"]), db, params={"pageSize": 100}
        )
        if not work:
            continue
        for w in work.get("courseWork", []):
            due = None
            if w.get("dueDate"):
                d = w["dueDate"]
                due = date(int(d["year"]), int(d["month"]), int(d["day"]))
            title = w.get("title", "Untitled")
            all_assignments.append(
                {
                    "id": w["id"],
                    "courseId": c["id"],
                    "courseName": c.get("name"),
                    "title": title,
                    "description": w.get("description", ""),
                    "dueDate": due.isoformat() if due else None,
                    "status": "Not started",
                }
            )
            # Merge (matched by google id, preserves manual status edits).
            existing = (
                db.query(Assignment)
                .filter(Assignment.google_id == w["id"])
                .first()
            )
            if existing:
                continue
            if local:
                db.add(
                    Assignment(
                        title=title,
                        description=w.get("description", "")[:500],
                        course_id=local.id,
                        due_date=due or date.today() + timedelta(days=7),
                        status="Not started",
                        google_id=w["id"],
                    )
                )
    db.commit()
    return {"assignments": all_assignments, "source": "live"}


# ---------------------------------------------------------------------------
# Deterministic mock fallbacks (offline / not connected)
# ---------------------------------------------------------------------------


def _mock_courses() -> list[dict]:
    return [
        {"id": "gc-1", "name": "Biology 101", "description": "Dr. Smith"},
        {"id": "gc-2", "name": "Chemistry", "description": "Prof. Johnson"},
        {"id": "gc-3", "name": "Mathematics", "description": "Ms. Williams"},
    ]


def _mock_assignments() -> list[dict]:
    now = datetime.now()
    day = timedelta(days=1)
    return [
        {
            "id": "gc-a1", "courseId": "gc-1", "courseName": "Biology 101",
            "title": "Cell Division Essay", "description": "1000-word essay on mitosis and meiosis",
            "dueDate": (now + 2 * day).date().isoformat(), "status": "Not started",
        },
        {
            "id": "gc-a2", "courseId": "gc-2", "courseName": "Chemistry",
            "title": "Chemical Reactions Homework", "description": "Problems 1-20 from Chapter 4",
            "dueDate": (now + 1 * day).date().isoformat(), "status": "Not started",
        },
        {
            "id": "gc-a3", "courseId": "gc-3", "courseName": "Mathematics",
            "title": "Calculus Problem Set 7", "description": "Integration problems",
            "dueDate": (now + 4 * day).date().isoformat(), "status": "Not started",
        },
    ]
