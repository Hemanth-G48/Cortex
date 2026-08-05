"""Teacher service: student stats aggregation and detail retrieval."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

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


def get_students_with_stats(db: Session) -> list[dict]:
    """Return per-student summary dicts with aggregated domain counts.

    Uses grouped COUNT queries (one per domain) then merges into a
    single dict per student — avoids the N+1 per-student query loop.
    """
    students = db.query(User).filter(User.role == "student").all()
    if not students:
        return []

    student_ids = [s.id for s in students]

    # Course counts per student (via user_id FK on Course)
    course_counts = (
        db.query(Course.user_id, func.count(Course.id))
        .filter(Course.user_id.in_(student_ids))
        .group_by(Course.user_id)
        .all()
    )
    course_map = {uid: cnt for uid, cnt in course_counts}

    # Assignment counts per student (join Assignment → Course → user_id)
    assignment_counts = (
        db.query(Course.user_id, func.count(Assignment.id))
        .join(Assignment, Assignment.course_id == Course.id)
        .filter(Course.user_id.in_(student_ids))
        .group_by(Course.user_id)
        .all()
    )
    assignment_map = {uid: cnt for uid, cnt in assignment_counts}

    # Task counts per student
    task_counts = (
        db.query(Task.user_id, func.count(Task.id))
        .filter(Task.user_id.in_(student_ids))
        .group_by(Task.user_id)
        .all()
    )
    task_map = {uid: cnt for uid, cnt in task_counts}

    # Book counts per student
    book_counts = (
        db.query(Book.user_id, func.count(Book.id))
        .filter(Book.user_id.in_(student_ids))
        .group_by(Book.user_id)
        .all()
    )
    book_map = {uid: cnt for uid, cnt in book_counts}

    # BrainDump existence per student (bool)
    braindump_rows = (
        db.query(BrainDump.user_id)
        .filter(BrainDump.user_id.in_(student_ids))
        .all()
    )
    braindump_set = {uid for uid, in braindump_rows}

    result: list[dict] = []
    for s in students:
        result.append({
            "id": s.id,
            "name": s.name,
            "stats": {
                "courses": course_map.get(s.id, 0),
                "assignments": assignment_map.get(s.id, 0),
                "todos": task_map.get(s.id, 0),
                "books": book_map.get(s.id, 0),
                "braindump": s.id in braindump_set,
            },
        })
    return result


def get_student_detail(db: Session, student_id: int) -> dict | None:
    """Return detailed data for a single student: assignments, todos,
    braindump content, and books.

    Returns ``None`` when no student exists with that id so the router can
    raise 404 (Phase 85: never fabricate an empty-but-200 detail payload).
    """
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if student is None:
        return None

    # Assignments resolved through the student's courses
    assignments = (
        db.query(Assignment)
        .join(Course, Assignment.course_id == Course.id)
        .filter(Course.user_id == student_id)
        .all()
    )
    assignment_list = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "status": a.status,
            "type": a.type,
            "file_url": a.file_url,
        }
        for a in assignments
    ]

    # Todos (Tasks)
    tasks = db.query(Task).filter(Task.user_id == student_id).all()
    todo_list = [
        {
            "id": t.id,
            "title": t.title,
            "subject_tag": t.subject_tag,
            "priority_tag": t.priority_tag,
            "priority_quadrant": t.priority_quadrant,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status,
        }
        for t in tasks
    ]

    # BrainDump
    braindump_row = db.query(BrainDump).filter(BrainDump.user_id == student_id).first()
    braindump = {"content": braindump_row.content} if braindump_row and braindump_row.content else None

    # Books
    books = db.query(Book).filter(Book.user_id == student_id).all()
    book_list = [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "category": b.category,
            "cover_url": b.cover_url,
            "file_url": b.file_url,
        }
        for b in books
    ]

    return {
        "id": student.id,
        "name": student.name,
        "assignments": assignment_list,
        "todos": todo_list,
        "braindump": braindump,
        "books": book_list,
    }
