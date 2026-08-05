"""Phase 85 — row-level ownership audit.

Every user-scoped STUDENT-PLANAR router (books, brain dumps, daily schedule,
notifications) must scope reads/writes to the authenticated user, and teacher
reads of student data must stay teacher-only. Cross-user access must yield
404 (missing row from the caller's perspective) or 403 (role blocked).
"""
from __future__ import annotations

from app.config import settings
from app.models import Notification, User
from sqlalchemy.orm import Session


def _signup(client, name: str, username: str, email: str, password: str = "pass123"):
    resp = client.post("/api/auth/signup", json={
        "name": name, "username": username, "email": email,
        "password": password, "role": "student",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _signup_teacher(client, monkeypatch) -> str:
    monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
    resp = client.post("/api/auth/signup", json={
        "name": "Teacher", "username": "own-teach", "email": "own-t@test.com",
        "password": "x", "role": "teacher", "teacher_secret": "secret",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _user(db_session: Session, username: str) -> User:
    return db_session.query(User).filter(User.username == username).first()


class TestBooksOwnership:
    def test_cross_user_update_and_delete_return_404(self, client):
        token_a = _signup(client, "Owner A", "own-a", "own-a@test.com")
        token_b = _signup(client, "Owner B", "own-b", "own-b@test.com")

        created = client.post(
            "/api/books",
            json={"title": "A's book", "author": "A", "category": "reading"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        book_id = created.json()["id"]

        put = client.put(
            f"/api/books/{book_id}",
            json={"category": "finished"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert put.status_code == 404

        delete = client.delete(
            f"/api/books/{book_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert delete.status_code == 404


class TestBrainDumpIsolation:
    def test_rows_are_one_per_user_and_private(self, client):
        token_a = _signup(client, "Dump A", "dump-a", "dump-a@test.com")
        token_b = _signup(client, "Dump B", "dump-b", "dump-b@test.com")

        put = client.put(
            "/api/braindumps/",
            json={"content": "A's private thoughts"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert put.status_code == 200

        # B has no row yet: placeholder, never A's content.
        get_b = client.get("/api/braindumps/", headers={"Authorization": f"Bearer {token_b}"})
        assert get_b.status_code == 200
        assert get_b.json()["content"] is None

        # B writing their own dump does not clobber A's row.
        client.put(
            "/api/braindumps/",
            json={"content": "B's thoughts"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        get_a = client.get("/api/braindumps/", headers={"Authorization": f"Bearer {token_a}"})
        assert get_a.json()["content"] == "A's private thoughts"


class TestDailyScheduleOwnership:
    def test_cross_user_update_toggle_delete_return_404(self, client):
        token_a = _signup(client, "Sched A", "sched-a", "sched-a@test.com")
        token_b = _signup(client, "Sched B", "sched-b", "sched-b@test.com")

        created = client.post(
            "/api/dailyschedule",
            json={
                "date": "2026-07-01",
                "time_range": "09:00-10:00",
                "activity": "Deep Work",
                "category": "Study Time",
                "energy": "High",
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert created.status_code == 201, created.text
        item_id = created.json()["id"]

        put = client.put(
            f"/api/dailyschedule/{item_id}",
            json={"activity": "Hacked"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert put.status_code == 404

        toggle = client.post(
            f"/api/dailyschedule/{item_id}/toggle",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert toggle.status_code == 404

        delete = client.delete(
            f"/api/dailyschedule/{item_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert delete.status_code == 404

        # B's list for the same date is empty.
        listing = client.get(
            "/api/dailyschedule",
            params={"date": "2026-07-01"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert listing.json() == []


class TestNotificationsOwnership:
    def test_notifications_are_scoped_to_the_recipient(self, client, db_session, monkeypatch):
        teacher = _signup_teacher(client, monkeypatch)
        token_a = _signup(client, "Notif A", "notif-a", "notif-a@test.com")
        token_b = _signup(client, "Notif B", "notif-b", "notif-b@test.com")

        student_a = _user(db_session, "notif-a")
        resp = client.post(
            "/api/teacher/broadcast/courses",
            json={"course": {"title": "Ownership Course"}, "student_ids": [student_a.id]},
            headers={"Authorization": f"Bearer {teacher}"},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] == 1

        unread_a = client.get(
            "/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert unread_a.json()["unread"] == 1
        unread_b = client.get(
            "/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert unread_b.json()["unread"] == 0

        notif = db_session.query(Notification).filter(
            Notification.title == "New course: Ownership Course"
        ).first()
        assert notif is not None

        mark_b = client.post(
            f"/api/notifications/{notif.id}/read",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert mark_b.status_code == 404
        delete_b = client.delete(
            f"/api/notifications/{notif.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert delete_b.status_code == 404

        mark_a = client.post(
            f"/api/notifications/{notif.id}/read",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert mark_a.status_code == 200
        assert mark_a.json()["read"] is True


class TestTeacherReadScope:
    def test_student_cannot_read_any_student_detail(self, client, db_session):
        token = _signup(client, "Det Stu", "det-stu", "det-stu@test.com")
        student = _user(db_session, "det-stu")
        resp = client.get(
            f"/api/teacher/students/{student.id}/detail",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_teacher_reads_only_existing_students(self, client, monkeypatch):
        teacher = _signup_teacher(client, monkeypatch)
        resp = client.get(
            "/api/teacher/students/999999/detail",
            headers={"Authorization": f"Bearer {teacher}"},
        )
        assert resp.status_code == 404
