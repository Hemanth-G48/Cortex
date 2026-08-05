"""Google Classroom sync (idempotent merge into Course/Assignment)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Course, User
from app.services import google_oauth

router = APIRouter(prefix="/api/classroom", tags=["classroom"])

CLASSROOM_COURSES_URL = "https://classroom.googleapis.com/v1/courses"
CLASSROOM_WORK_URL = "https://classroom.googleapis.com/v1/courses/{cid}/courseWork"


@router.get("/courses")
def classroom_courses(db: Session = Depends(get_db)) -> list[dict]:
    """Fetch Classroom courses; merge into the local Course table by google_id."""
    data = google_oauth.authorized_get(CLASSROOM_COURSES_URL, db, params={"pageSize": 100, "courseStates": "ACTIVE"})
    if data is None:
        return _mock_courses()  # not connected → deterministic mock fallback

    formatted: list[dict] = []
    for c in data.get("courses", []):
        formatted.append({
            "id": c["id"],
            "name": c.get("name"),
            "description": c.get("descriptionHeading") or c.get("description"),
        })
        # Idempotent merge (matched by google id, preserves manual edits).
        existing = db.query(Course).filter(Course.google_id == c["id"]).first()
        if existing:
            existing.title = c.get("name") or existing.title
        else:
            user = db.query(User).first()
            db.add(Course(
                title=c.get("name") or "Google Classroom Course",
                status="In progress",
                google_id=c["id"],
                user_id=user.id if user else None,
            ))
    db.commit()
    return formatted


@router.get("/assignments")
def classroom_assignments(db: Session = Depends(get_db)) -> list[dict]:
    """Fetch course work across all courses; merge into Assignment by google_id."""
    courses_data = google_oauth.authorized_get(
        CLASSROOM_COURSES_URL, db, params={"pageSize": 100, "courseStates": "ACTIVE"}
    )
    if courses_data is None:
        return _mock_assignments()

    all_assignments: list[dict] = []
    for c in courses_data.get("courses", []):
        local = db.query(Course).filter(Course.google_id == c["id"]).first()
        work = google_oauth.authorized_get(CLASSROOM_WORK_URL.format(cid=c["id"]), db, params={"pageSize": 100})
        if not work:
            continue
        for w in work.get("courseWork", []):
            due = None
            if w.get("dueDate"):
                d = w["dueDate"]
                due = date(int(d["year"]), int(d["month"]), int(d["day"]))
            title = w.get("title", "Untitled")
            formatted = {
                "id": w["id"],
                "courseId": c["id"],
                "courseName": c.get("name"),
                "title": title,
                "description": w.get("description", ""),
                "dueDate": due.isoformat() if due else None,
                "status": "Not started",
            }
            all_assignments.append(formatted)
            # Merge (matched by google id, preserves manual status edits).
            existing = db.query(Assignment).filter(Assignment.google_id == w["id"]).first()
            if existing:
                continue
            if local:
                db.add(Assignment(
                    title=title,
                    description=w.get("description", "")[:500],
                    course_id=local.id,
                    due_date=due or date.today() + timedelta(days=7),
                    status="Not started",
                    google_id=w["id"],
                ))
    db.commit()
    return all_assignments


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
