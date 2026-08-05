"""Teacher router: student management and broadcast endpoints."""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi import File, Form
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Assignment,
    Book,
    BrainDump,
    Course,
    DailyScheduleItem,
    Notification,
    Task,
    User,
)
from app.services.security import require_teacher
from app.services.teacher import get_student_detail, get_students_with_stats

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _parse_date(value: object) -> date | None:
    """Parse an ISO date string (or pass through a date object) for Date columns."""
    if isinstance(value, date) and not isinstance(value, str):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return None


def _store_upload(file: UploadFile) -> str:
    """Persist an uploaded file under UPLOAD_DIR with a random hex name."""
    original = Path(file.filename or "file.txt").name
    suffix = Path(original).suffix.lower()
    directory = Path(settings.UPLOAD_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = directory / stored_name
    data = file.file.read()
    with target.open("wb") as out:
        out.write(data)
    return f"/uploads/{stored_name}"


# ---------------------------------------------------------------------------
# Student list with stats
# ---------------------------------------------------------------------------

@router.get("/students")
def list_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> list[dict]:
    return get_students_with_stats(db)


# ---------------------------------------------------------------------------
# Student detail
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/detail")
def student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    detail = get_student_detail(db, student_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return detail


# ---------------------------------------------------------------------------
# Broadcast: courses
# ---------------------------------------------------------------------------

@router.post("/broadcast/courses")
def broadcast_courses(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    course_data = body.get("course", {})
    student_ids = body.get("student_ids")

    targets = _resolve_targets(db, student_ids, current_user.id)

    for target in targets:
        course = Course(
            title=course_data.get("title", ""),
            current_assignment=course_data.get("current_assignment", 0),
            total_assignments=course_data.get("total_assignments", 0),
            next_exam=course_data.get("next_exam"),
            total_exams=course_data.get("total_exams", 0),
            status=course_data.get("status", "Not started"),
            user_id=target.id,
        )
        db.add(course)
        db.flush()
        db.add(
            Notification(
                user_id=target.id,
                kind="broadcast",
                title=f"New course: {course.title}",
                ref_type="course",
                ref_id=course.id,
            )
        )

    db.commit()
    return {"created": len(targets)}


# ---------------------------------------------------------------------------
# Broadcast: assignments (multipart)
# ---------------------------------------------------------------------------

@router.post("/broadcast/assignments")
def broadcast_assignments(
    assignment: str = Form(...),
    student_ids: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    data = json.loads(assignment)
    target_ids = json.loads(student_ids) if student_ids else None

    due_date = _parse_date(data.get("due_date"))
    if due_date is None:
        raise HTTPException(400, detail={"error": "due_date is required"})

    targets = _resolve_targets(db, target_ids, current_user.id)

    file_url = None
    if file and file.filename:
        file_url = _store_upload(file)

    for target in targets:
        course_id = data.get("course_id")
        assignment_obj = Assignment(
            title=data.get("title", ""),
            description=data.get("description"),
            course_id=course_id,
            due_date=due_date,
            status=data.get("status", "Not started"),
            type=data.get("type", "Homework"),
            file_url=file_url,
        )
        db.add(assignment_obj)
        db.flush()
        db.add(
            Notification(
                user_id=target.id,
                kind="broadcast",
                title=f"New assignment: {assignment_obj.title}",
                ref_type="assignment",
                ref_id=assignment_obj.id,
            )
        )

    db.commit()
    return {"created": len(targets)}


# ---------------------------------------------------------------------------
# Broadcast: todos
# ---------------------------------------------------------------------------

@router.post("/broadcast/todos")
def broadcast_todos(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    todo_data = body.get("todo", {})
    student_ids = body.get("student_ids")

    targets = _resolve_targets(db, student_ids, current_user.id)

    for target in targets:
        task = Task(
            title=todo_data.get("title", ""),
            subject_tag=todo_data.get("subject_tag"),
            priority_tag=todo_data.get("priority_tag"),
            priority_quadrant=todo_data.get("priority_quadrant", "Important/Not Urgent"),
            due_date=_parse_date(todo_data.get("due_date")),
            status="Not started",
            user_id=target.id,
        )
        db.add(task)
        db.add(
            Notification(
                user_id=target.id,
                kind="broadcast",
                title=f"New todo: {task.title}",
                ref_type="todo",
                ref_id=task.id,
            )
        )

    db.commit()
    return {"created": len(targets)}


# ---------------------------------------------------------------------------
# Broadcast: books (multipart)
# ---------------------------------------------------------------------------

@router.post("/broadcast/books")
def broadcast_books(
    book: str = Form(...),
    student_ids: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    data = json.loads(book)
    target_ids = json.loads(student_ids) if student_ids else None

    targets = _resolve_targets(db, target_ids, current_user.id)

    file_url = None
    if file and file.filename:
        file_url = _store_upload(file)

    for target in targets:
        book_obj = Book(
            user_id=target.id,
            title=data.get("title", ""),
            author=data.get("author"),
            category=data.get("category"),
            file_url=file_url,
        )
        db.add(book_obj)
        db.add(
            Notification(
                user_id=target.id,
                kind="broadcast",
                title=f"New book: {book_obj.title}",
                ref_type="book",
                ref_id=book_obj.id,
            )
        )

    db.commit()
    return {"created": len(targets)}


# ---------------------------------------------------------------------------
# Broadcast: schedule
# ---------------------------------------------------------------------------

@router.post("/broadcast/schedule")
def broadcast_schedule(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
) -> dict:
    item_data = body.get("item", {})
    student_ids = body.get("student_ids")

    targets = _resolve_targets(db, student_ids, current_user.id)

    for target in targets:
        item = DailyScheduleItem(
            user_id=target.id,
            date=_parse_date(item_data.get("date")),
            time_range=item_data.get("time_range", ""),
            activity=item_data.get("activity", ""),
            category=item_data.get("category"),
            cat_class=item_data.get("cat_class") or (
                f"cat-{item_data.get('category', '').lower().replace(' ', '-')}"
                if item_data.get("category") else None
            ),
            location=item_data.get("location"),
            energy=item_data.get("energy"),
            e_class=item_data.get("e_class") or (
                f"e-{item_data.get('energy', '').lower()}"
                if item_data.get("energy") else None
            ),
            notes=item_data.get("notes"),
        )
        db.add(item)
        db.add(
            Notification(
                user_id=target.id,
                kind="broadcast",
                title=f"New schedule: {item.activity}",
                ref_type="schedule",
                ref_id=item.id,
            )
        )

    db.commit()
    return {"created": len(targets)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_targets(
    db: Session,
    student_ids: list[int] | None,
    teacher_id: int,
) -> list[User]:
    """Return target students: explicit list or all students except the teacher."""
    if student_ids:
        return db.query(User).filter(User.id.in_(student_ids), User.role == "student").all()
    return db.query(User).filter(User.role == "student", User.id != teacher_id).all()
