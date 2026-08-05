"""End-to-end cross-role flow (Phase 96): teacher broadcast -> student notification
-> student completes -> teacher stats update.

This exercises the full teacher->student sync loop against the TestClient using
the same helpers as test_teacher.py.
"""

import json

from app.config import settings
from app.models import Course
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signup_teacher(client, monkeypatch) -> str:
    monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
    resp = client.post("/api/auth/signup", json={
        "name": "Prof Flow",
        "username": "flowteacher",
        "email": "flow.t@test.com",
        "password": "x",
        "role": "teacher",
        "teacher_secret": "secret",
    })
    assert resp.status_code == 201, f"Teacher signup failed: {resp.json()}"
    return resp.json()["token"]


def _signup_student(client, name: str, username: str, email: str) -> tuple[str, int]:
    resp = client.post("/api/auth/signup", json={
        "name": name,
        "username": username,
        "email": email,
        "password": "x",
        "role": "student",
    })
    assert resp.status_code == 201, f"Student signup failed: {resp.json()}"
    token = resp.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.json()
    return token, me.json()["user"]["id"]


# ---------------------------------------------------------------------------
# Teacher -> student -> teacher loop
# ---------------------------------------------------------------------------

def test_teacher_broadcast_student_completes_teacher_sees_stats(
    client, db_session, monkeypatch,
):
    teacher_token = _signup_teacher(client, monkeypatch)
    student_token, student_id = _signup_student(client, "Flow Student", "flowstu", "flow.s@test.com")

    auth_teacher = {"Authorization": f"Bearer {teacher_token}"}
    auth_student = {"Authorization": f"Bearer {student_token}"}

    # --- Teacher broadcasts a course, then an assignment + book for that course ---
    course_resp = client.post(
        "/api/teacher/broadcast/courses",
        json={"course": {"title": "Linear Algebra", "status": "In progress"}, "student_ids": [student_id]},
        headers=auth_teacher,
    )
    assert course_resp.status_code == 200, course_resp.json()
    assert course_resp.json()["created"] == 1

    # Find the course the student just received so the assignment can attach to it.
    course = db_session.query(Course).filter(Course.user_id == student_id).first()
    assert course is not None

    assign_resp = client.post(
        "/api/teacher/broadcast/assignments",
        data={
            "assignment": json.dumps({
                "title": "Chapter 5 Problems",
                "description": "Complete odd-numbered problems",
                "type": "Homework",
                "status": "Not started",
                "due_date": "2026-08-15",
                "course_id": course.id,
            }),
            "student_ids": json.dumps([student_id]),
        },
        headers=auth_teacher,
    )
    assert assign_resp.status_code == 200, assign_resp.json()
    assert assign_resp.json()["created"] == 1

    book_resp = client.post(
        "/api/teacher/broadcast/books",
        data={
            "book": json.dumps({"title": "Linear Algebra", "author": "Strang", "category": "reading"}),
            "student_ids": json.dumps([student_id]),
        },
        headers=auth_teacher,
    )
    assert book_resp.status_code == 200, book_resp.json()
    assert book_resp.json()["created"] == 1

    # --- Student sees the notifications ---
    notif_resp = client.get("/api/notifications", headers=auth_student)
    assert notif_resp.status_code == 200
    notifs = notif_resp.json()
    titles = [n["title"] for n in notifs]
    assert any("Chapter 5 Problems" in t for t in titles), titles
    assert any("Linear Algebra" in t for t in titles), titles

    # --- Student finds and completes the broadcast assignment ---
    assign_list = client.get("/api/assignments", headers=auth_student).json()
    broadcast = [a for a in assign_list if a["title"] == "Chapter 5 Problems"]
    assert broadcast, "student should see the broadcast assignment"
    assignment_id = broadcast[0]["id"]
    assert broadcast[0]["status"] == "Not started"

    complete = client.post(
        f"/api/assignments/{assignment_id}/complete", headers=auth_student,
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "Completed"

    # --- Teacher detail reflects the completed assignment + book ---
    detail = client.get(
        f"/api/teacher/students/{student_id}/detail", headers=auth_teacher,
    )
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == student_id
    assert any(a["title"] == "Chapter 5 Problems" and a["status"] == "Completed" for a in data["assignments"])
    assert any(b["title"] == "Linear Algebra" for b in data["books"])

    # --- Teacher student list stats reflect the broadcast ---
    students = client.get("/api/teacher/students", headers=auth_teacher).json()
    by_id = {s["id"]: s for s in students}
    assert student_id in by_id
    assert by_id[student_id]["stats"]["books"] >= 1
    assert by_id[student_id]["stats"]["assignments"] >= 1


def test_student_cannot_call_teacher_endpoints(client, monkeypatch):
    """Students must be rejected from the teacher surface entirely."""
    teacher_token = _signup_teacher(client, monkeypatch)
    student_token, _ = _signup_student(client, "Blocked Student", "blockstu", "block.s@test.com")

    auth_student = {"Authorization": f"Bearer {student_token}"}
    resp = client.get("/api/teacher/students", headers=auth_student)
    assert resp.status_code == 403
    resp = client.post(
        "/api/teacher/broadcast/courses",
        json={"course": {"title": "X"}, "student_ids": []},
        headers=auth_student,
    )
    assert resp.status_code == 403
