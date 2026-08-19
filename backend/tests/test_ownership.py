"""Phase 85 — row-level ownership audit (single-owner app).

Every user-scoped STUDENT-PLANAR router (books, brain dumps, daily schedule,
notifications) scopes reads/writes to the single owner (the first ``users``
row). Cross-user access is gone with multi-user auth; the assertions below
verify that in a tokenless request the owner's data is reachable and that
stale teacher-surface routes are no longer mounted.
"""
from __future__ import annotations

from app.models import Notification, User
from sqlalchemy.orm import Session


def _signup(client, name: str, username: str, email: str, password: str = "pass123"):
    resp = client.post("/api/auth/signup", json={
        "name": name, "username": username, "email": email,
        "password": password, "role": "student",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _owner(db_session: Session) -> User:
    return db_session.query(User).order_by(User.id).first()


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
    def test_notifications_are_scoped_to_the_owner(self, client, db_session):
        """Single owner: notifications resolve to the first user, no tokens."""
        owner = _owner(db_session)
        notif = Notification(
            user_id=owner.id,
            kind="broadcast",
            title="New course: Ownership Course",
            body="A new course is available.",
        )
        db_session.add(notif)
        db_session.commit()

        unread = client.get("/api/notifications/unread-count")
        assert unread.status_code == 200
        assert unread.json()["unread"] == 1

        listing = client.get("/api/notifications")
        assert listing.status_code == 200
        titles = [n["title"] for n in listing.json()]
        assert "New course: Ownership Course" in titles

        mark = client.post(f"/api/notifications/{notif.id}/read")
        assert mark.status_code == 200
        assert mark.json()["read"] is True


class TestTeacherSurfaceRemoved:
    def test_teacher_routes_are_not_mounted(self, client, db_session):
        """Single-user app: the teacher broadcast/student-detail surface is gone."""
        resp = client.get("/api/teacher/students")
        assert resp.status_code == 404
        resp = client.post(
            "/api/teacher/broadcast/courses",
            json={"course": {"title": "X"}, "student_ids": []},
        )
        assert resp.status_code == 404
