"""Tests for G11 analytics: assignment analytics (Phase 72), book insights
trend (Phase 71), and computed course progress (Phase 76).
"""

from datetime import date

from sqlalchemy.orm import Session

from app.models import Assignment, Book, Course, User


def _get_token(client) -> str:
    resp = client.post("/api/auth/login", json={})
    return resp.json()["token"]


def _first_user(db_session: Session) -> User:
    return db_session.query(User).order_by(User.id).first()


def _make_course(db_session: Session, title: str, user_id: int) -> Course:
    course = Course(title=title, user_id=user_id)
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


def _make_assignment(db_session: Session, title: str, course_id: int, status: str) -> Assignment:
    assignment = Assignment(title=title, course_id=course_id, due_date=date(2026, 9, 1), status=status)
    db_session.add(assignment)
    db_session.commit()
    db_session.refresh(assignment)
    return assignment


# ---------------------------------------------------------------------------
# Phase 72 — GET /api/assignments/analytics
# ---------------------------------------------------------------------------

def test_assignment_analytics_per_course(client, db_session: Session):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    user = _first_user(db_session)

    course = _make_course(db_session, "Analytics Course", user.id)
    _make_assignment(db_session, "A1", course.id, "Completed")
    _make_assignment(db_session, "A2", course.id, "Not started")

    resp = client.get("/api/assignments/analytics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    row = next((c for c in data["per_course"] if c["course_id"] == course.id), None)
    assert row is not None, data["per_course"]
    assert row["total"] == 2
    assert row["done"] == 1
    assert row["done_ratio"] == 0.5

    assert "overall" in data
    assert data["overall"]["total"] >= 2
    assert data["overall"]["done"] >= 1
    assert isinstance(data["overall"]["completion_pct"], float)


def test_assignment_analytics_works_without_auth(client):
    """Single-user app: analytics resolve to the owner without a token."""
    resp = client.get("/api/assignments/analytics")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Phase 71 — book insights include per-author + added_this_month
# ---------------------------------------------------------------------------

def test_book_insights_trend(client, db_session: Session):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    user = _first_user(db_session)

    db_session.add(Book(user_id=user.id, title="Haskell Book", author="Marlow", category="finished"))
    db_session.add(Book(user_id=user.id, title="Another Haskell", author="Marlow", category="want"))
    db_session.add(Book(user_id=user.id, title="Rust", author="Klabnik", category="reading"))
    db_session.commit()

    resp = client.get("/api/books/insights", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["per_author"].get("Marlow") == 2
    assert data["per_author"].get("Klabnik") == 1
    # server_default created_at = now() -> the books land in the current month.
    assert data["added_this_month"] >= 3


# ---------------------------------------------------------------------------
# Phase 76 — computed course progress
# ---------------------------------------------------------------------------

def test_course_progress_computed(client, db_session: Session):
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    user = _first_user(db_session)

    course = _make_course(db_session, "Progress Course", user.id)
    _make_assignment(db_session, "P1", course.id, "Completed")
    _make_assignment(db_session, "P2", course.id, "Completed")
    _make_assignment(db_session, "P3", course.id, "Not started")

    resp = client.get("/api/courses/", headers=headers)
    assert resp.status_code == 200
    row = next((c for c in resp.json() if c["title"] == "Progress Course"), None)
    assert row is not None
    assert row["progress_percentage"] == 66.7  # 2/3 * 100 rounded to 1 dp
