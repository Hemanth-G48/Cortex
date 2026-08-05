"""Tests for the teacher API endpoints."""

import json
from datetime import date

import pytest
from app.config import settings
from app.models import Assignment, Book, Course, DailyScheduleItem, Notification, Task, User
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_token(client) -> str:
    """Return the first user's token (Alex, a student)."""
    resp = client.post("/api/auth/login", json={})
    return resp.json()["token"]


def _signup_teacher(client, monkeypatch) -> str:
    """Sign up a teacher and return the bearer token."""
    monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
    resp = client.post("/api/auth/signup", json={
        "name": "Teacher",
        "username": "teach",
        "email": "t@t.com",
        "password": "x",
        "role": "teacher",
        "teacher_secret": "secret",
    })
    assert resp.status_code == 201, f"Teacher signup failed: {resp.json()}"
    return resp.json()["token"]


def _signup_student(client, name: str, username: str, email: str) -> str:
    """Sign up a student and return the bearer token."""
    resp = client.post("/api/auth/signup", json={
        "name": name,
        "username": username,
        "email": email,
        "password": "x",
        "role": "student",
    })
    assert resp.status_code == 201, f"Student signup failed: {resp.json()}"
    return resp.json()["token"]


# ---------------------------------------------------------------------------
# GET /api/teacher/students
# ---------------------------------------------------------------------------

def test_get_students_teacher_token(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)

    # Create two students via signup
    _signup_student(client, "Student One", "stu1", "s1@test.com")
    _signup_student(client, "Student Two", "stu2", "s2@test.com")

    # Give student 2 a book and a task directly
    resp = client.post("/api/auth/login", json={})
    all_users = client.get("/api/auth/me", headers={"Authorization": f"Bearer {teacher_token}"})
    # Use raw db_session to find student ids
    users = db_session.query(__import__("app.models", fromlist=["User"]).User).filter(
        __import__("app.models", fromlist=["User"]).User.role == "student"
    ).all()
    # There should be at least 2 students (the two signups) plus Alex
    student_users = [u for u in users if u.username in ("stu1", "stu2")]
    assert len(student_users) >= 2

    stu2 = student_users[1]
    db_session.add(Book(user_id=stu2.id, title="Test Book", author="Author", category="want"))
    db_session.add(Task(user_id=stu2.id, title="Test Task", status="Not started"))
    db_session.commit()

    resp = client.get("/api/teacher/students", headers={
        "Authorization": f"Bearer {teacher_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Find the two students we created
    by_name = {u["name"]: u for u in data}
    assert "Student One" in by_name
    assert "Student Two" in by_name
    # Student Two should have 1 book and 1 todo
    assert by_name["Student Two"]["stats"]["books"] == 1
    assert by_name["Student Two"]["stats"]["todos"] == 1
    # Student One should have 0 books and 0 todos
    assert by_name["Student One"]["stats"]["books"] == 0
    assert by_name["Student One"]["stats"]["todos"] == 0


def test_get_students_student_token_returns_403(client, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    student_token = _signup_student(client, "Stu", "stu3", "s3@test.com")

    resp = client.get("/api/teacher/students", headers={
        "Authorization": f"Bearer {student_token}",
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/teacher/students/{student_id}/detail
# ---------------------------------------------------------------------------

def test_get_student_detail_returns_assignments_todos_braindump_books(
    client, db_session, monkeypatch
):
    teacher_token = _signup_teacher(client, monkeypatch)
    token = _signup_student(client, "Detail Student", "det Stu", "det@test.com")

    # Find the student id
    from app.models import User
    student = db_session.query(User).filter(User.username == "det Stu").first()
    assert student is not None

    # Add a course + assignment for this student
    from app.models import Course, Assignment
    course = Course(title="Math", user_id=student.id)
    db_session.add(course)
    db_session.flush()
    db_session.add(Assignment(
        title="Homework 1",
        course_id=course.id,
        due_date=date(2026, 6, 1),
        status="Not started",
        type="Homework",
    ))

    # Add a task
    db_session.add(Task(
        user_id=student.id,
        title="Buy groceries",
        status="Not started",
        priority_quadrant="Important/Not Urgent",
    ))

    # Add a brain dump
    from app.models import BrainDump
    db_session.add(BrainDump(user_id=student.id, content="My thoughts"))

    # Add a book
    db_session.add(Book(user_id=student.id, title="Clean Code", author="Martin", category="finished"))

    db_session.commit()

    resp = client.get(f"/api/teacher/students/{student.id}/detail", headers={
        "Authorization": f"Bearer {teacher_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Student"
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["title"] == "Homework 1"
    assert len(data["todos"]) == 1
    assert data["todos"][0]["title"] == "Buy groceries"
    assert data["braindump"] == {"content": "My thoughts"}
    assert len(data["books"]) == 1
    assert data["books"][0]["title"] == "Clean Code"


# ---------------------------------------------------------------------------
# POST /api/teacher/broadcast/courses
# ---------------------------------------------------------------------------

def test_broadcast_courses_to_selected_students(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    t1 = _signup_student(client, "Course Stu 1", "cs1", "cs1@test.com")
    t2 = _signup_student(client, "Course Stu 2", "cs2", "cs2@test.com")

    # Resolve student ids
    from app.models import User
    s1 = db_session.query(User).filter(User.username == "cs1").first()
    s2 = db_session.query(User).filter(User.username == "cs2").first()

    before = db_session.query(Notification).count()

    resp = client.post("/api/teacher/broadcast/courses", json={
        "course": {"title": "Broadcast Math", "status": "In progress"},
        "student_ids": [s1.id, s2.id],
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    # Verify courses created
    courses = db_session.query(Course).filter(Course.title == "Broadcast Math").all()
    assert len(courses) == 2
    assert {c.user_id for c in courses} == {s1.id, s2.id}

    # Verify notifications
    after = db_session.query(Notification).count()
    assert after == before + 2
    notifs = db_session.query(Notification).filter(Notification.title == "New course: Broadcast Math").all()
    assert len(notifs) == 2


def test_broadcast_courses_no_student_ids_targets_all(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    _signup_student(client, "All Stu 1", "all1", "all1@test.com")
    _signup_student(client, "All Stu 2", "all2", "all2@test.com")

    from app.models import User
    teacher = db_session.query(User).filter(User.username == "teach").first()
    before = db_session.query(Notification).count()

    resp = client.post("/api/teacher/broadcast/courses", json={
        "course": {"title": "General Science"},
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    # Should target all students except the teacher
    assert resp.json()["created"] >= 2

    after = db_session.query(Notification).count()
    assert after == before + resp.json()["created"]


# ---------------------------------------------------------------------------
# POST /api/teacher/broadcast/assignments (multipart)
# ---------------------------------------------------------------------------

def test_broadcast_assignments_multipart_with_file(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    t1 = _signup_student(client, "File Stu 1", "fs1", "fs1@test.com")
    t2 = _signup_student(client, "File Stu 2", "fs2", "fs2@test.com")

    from app.models import User
    s1 = db_session.query(User).filter(User.username == "fs1").first()
    s2 = db_session.query(User).filter(User.username == "fs2").first()

    before = db_session.query(Notification).count()

    assignment_json = json.dumps({
        "title": "File Assignment",
        "description": "Upload a PDF",
        "due_date": "2026-06-15",
        "status": "Not started",
        "type": "Homework",
    })

    resp = client.post("/api/teacher/broadcast/assignments", data={
        "assignment": assignment_json,
        "student_ids": json.dumps([s1.id, s2.id]),
    }, files={
        "file": ("test.pdf", b"%PDF-fake-pdf-content", "application/pdf"),
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    # Verify assignments created with file_url
    assignments = db_session.query(Assignment).filter(Assignment.title == "File Assignment").all()
    assert len(assignments) == 2
    for a in assignments:
        assert a.file_url is not None
        assert a.file_url.startswith("/uploads/")

    # Verify notifications
    after = db_session.query(Notification).count()
    assert after == before + 2


# ---------------------------------------------------------------------------
# POST /api/teacher/broadcast/todos
# ---------------------------------------------------------------------------

def test_broadcast_todos_creates_tasks(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    t1 = _signup_student(client, "Todo Stu 1", "ts1", "ts1@test.com")

    from app.models import User
    s1 = db_session.query(User).filter(User.username == "ts1").first()

    before = db_session.query(Notification).count()

    resp = client.post("/api/teacher/broadcast/todos", json={
        "todo": {"title": "Study chapter 5", "priority_tag": "High", "subject_tag": "Math"},
        "student_ids": [s1.id],
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    tasks = db_session.query(Task).filter(Task.title == "Study chapter 5").all()
    assert len(tasks) == 1
    assert tasks[0].status == "Not started"
    assert tasks[0].priority_quadrant == "Important/Not Urgent"

    after = db_session.query(Notification).count()
    assert after == before + 1


# ---------------------------------------------------------------------------
# POST /api/teacher/broadcast/books (multipart)
# ---------------------------------------------------------------------------

def test_broadcast_books_multipart_with_file(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    t1 = _signup_student(client, "Book Stu 1", "bs1", "bs1@test.com")

    from app.models import User
    s1 = db_session.query(User).filter(User.username == "bs1").first()

    before = db_session.query(Notification).count()

    book_json = json.dumps({
        "title": "The Art of Programming",
        "author": "Donald Knuth",
        "category": "finished",
    })

    resp = client.post("/api/teacher/broadcast/books", data={
        "book": book_json,
        "student_ids": json.dumps([s1.id]),
    }, files={
        "file": ("book.pdf", b"%PDF-book-content", "application/pdf"),
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    books = db_session.query(Book).filter(Book.title == "The Art of Programming").all()
    assert len(books) == 1
    assert books[0].file_url is not None
    assert books[0].file_url.startswith("/uploads/")

    after = db_session.query(Notification).count()
    assert after == before + 1


# ---------------------------------------------------------------------------
# POST /api/teacher/broadcast/schedule
# ---------------------------------------------------------------------------

def test_broadcast_schedule_creates_daily_schedule_items(client, db_session, monkeypatch):
    teacher_token = _signup_teacher(client, monkeypatch)
    t1 = _signup_student(client, "Sched Stu 1", "ss1", "ss1@test.com")

    from app.models import User
    s1 = db_session.query(User).filter(User.username == "ss1").first()

    before = db_session.query(Notification).count()

    resp = client.post("/api/teacher/broadcast/schedule", json={
        "item": {
            "date": "2026-06-01",
            "time_range": "09:00-10:30",
            "activity": "Morning Math",
            "category": "Study Time",
            "energy": "High",
            "location": "Library",
            "notes": "Bring notebook",
        },
        "student_ids": [s1.id],
    }, headers={"Authorization": f"Bearer {teacher_token}"})
    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    items = db_session.query(DailyScheduleItem).filter(
        DailyScheduleItem.activity == "Morning Math"
    ).all()
    assert len(items) == 1
    assert items[0].category == "Study Time"
    assert items[0].cat_class == "cat-study-time"
    assert items[0].energy == "High"
    assert items[0].e_class == "e-high"

    after = db_session.query(Notification).count()
    assert after == before + 1