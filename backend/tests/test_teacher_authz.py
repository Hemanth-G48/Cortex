"""Phase 88 — teacher authorization matrix tests.

The matrix under test (students = any non-teacher):
  | caller          | /api/teacher/*            |
  |-----------------|---------------------------|
  | unauthenticated | 401                       |
  | student         | 403 (every endpoint)      |
  | teacher         | 200 / broadcast works     |

Additional invariant: broadcasts only ever target student rows — a teacher id
in ``student_ids`` is ignored (0 created).
"""
from __future__ import annotations

import json

from app.config import settings
from app.models import User
from sqlalchemy.orm import Session


def _signup_student(client, name: str, username: str, email: str) -> str:
    resp = client.post("/api/auth/signup", json={
        "name": name, "username": username, "email": email,
        "password": "x", "role": "student",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _signup_teacher(client, monkeypatch, username: str = "matrix-teach") -> str:
    monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
    resp = client.post("/api/auth/signup", json={
        "name": "Matrix Teacher", "username": username,
        "email": f"{username}@test.com", "password": "x",
        "role": "teacher", "teacher_secret": "secret",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


JSON_ENDPOINTS = [
    ("get", "/api/teacher/students"),
    ("get", "/api/teacher/students/1/detail"),
    ("post", "/api/teacher/broadcast/courses"),
    ("post", "/api/teacher/broadcast/todos"),
    ("post", "/api/teacher/broadcast/schedule"),
]


class TestUnauthenticated:
    def test_all_teacher_endpoints_require_auth(self, client):
        for method, path in JSON_ENDPOINTS:
            resp = getattr(client, method)(path)
            assert resp.status_code == 401, f"{method.upper()} {path} -> {resp.status_code}"

    def test_multipart_teacher_endpoints_require_auth(self, client):
        for path in ("/api/teacher/broadcast/assignments", "/api/teacher/broadcast/books"):
            resp = client.post(path, data={"book": json.dumps({})})
            assert resp.status_code == 401, f"POST {path} -> {resp.status_code}"


class TestStudentBlocked:
    def test_student_rejected_on_json_endpoints(self, client):
        token = _signup_student(client, "Blocked Stu", "blocked-stu", "blocked-stu@test.com")
        for method, path in JSON_ENDPOINTS:
            resp = getattr(client, method)(
                path, headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 403, f"{method.upper()} {path} -> {resp.status_code}"

    def test_student_rejected_on_multipart_broadcasts(self, client):
        token = _signup_student(client, "Blocked Stu2", "blocked-stu2", "blocked-stu2@test.com")
        for path in ("/api/teacher/broadcast/assignments", "/api/teacher/broadcast/books"):
            resp = client.post(
                path,
                data={"book": json.dumps({"title": "x"})},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403, f"POST {path} -> {resp.status_code}"


class TestTeacherAllowed:
    def test_teacher_reaches_students_endpoint(self, client, monkeypatch):
        teacher = _signup_teacher(client, monkeypatch)
        resp = client.get(
            "/api/teacher/students",
            headers={"Authorization": f"Bearer {teacher}"},
        )
        assert resp.status_code == 200

    def test_broadcast_never_targets_teachers(self, client, db_session: Session, monkeypatch):
        teacher_token = _signup_teacher(client, monkeypatch)
        teacher = db_session.query(User).filter(User.username == "matrix-teach").first()
        assert teacher is not None

        resp = client.post(
            "/api/teacher/broadcast/courses",
            json={"course": {"title": "Teacher-Only Course"}, "student_ids": [teacher.id]},
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] == 0

    def test_student_ids_filter_to_students_only(self, client, db_session: Session, monkeypatch):
        teacher_token = _signup_teacher(client, monkeypatch)
        _signup_student(client, "Target Stu", "target-stu", "target-stu@test.com")
        student = db_session.query(User).filter(User.username == "target-stu").first()
        teacher = db_session.query(User).filter(User.username == "matrix-teach").first()

        resp = client.post(
            "/api/teacher/broadcast/courses",
            json={
                "course": {"title": "Mixed Targets"},
                "student_ids": [student.id, teacher.id],  # teacher id is ignored
            },
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] == 1
