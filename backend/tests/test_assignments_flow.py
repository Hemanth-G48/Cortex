"""Tests for STUDENT-PLANAR G6 assignment flow endpoints (Phases 38-40)."""
from __future__ import annotations

import io

import pytest
from datetime import date

from app.models import Assignment, Course


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _seed_assignment(db):
    """Create a course and assignment, return the assignment."""
    course = Course(title="C")
    db.add(course)
    db.flush()
    assignment = Assignment(
        title="A",
        course_id=course.id,
        due_date=date.today(),
        status="Not started",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


SAMPLE_PDF = b"%PDF-1.4 fake pdf content"
SAMPLE_EXE = b"MZ fake exe content"


# ---------------------------------------------------------------------------
# POST /api/assignments/{id}/status
# ---------------------------------------------------------------------------

class TestStatusUpdate:
    def test_sets_in_progress(self, client, db_session):
        assignment = _seed_assignment(db_session)
        resp = client.post(f"/api/assignments/{assignment.id}/status", json={"status": "In progress"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "In progress"
        # Persists: GET list shows it
        list_resp = client.get("/api/assignments")
        assert list_resp.status_code == 200
        items = list_resp.json()
        match = [a for a in items if a["id"] == assignment.id]
        assert len(match) == 1
        assert match[0]["status"] == "In progress"

    def test_invalid_status_returns_400(self, client, db_session):
        assignment = _seed_assignment(db_session)
        resp = client.post(f"/api/assignments/{assignment.id}/status", json={"status": "Unknown"})
        assert resp.status_code == 400

    def test_status_not_found_returns_404(self, client):
        resp = client.post("/api/assignments/9999/status", json={"status": "In progress"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/assignments/{id}/complete
# ---------------------------------------------------------------------------

class TestComplete:
    def test_sets_completed(self, client, db_session):
        assignment = _seed_assignment(db_session)
        resp = client.post(f"/api/assignments/{assignment.id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"

    def test_complete_not_found_returns_404(self, client):
        resp = client.post("/api/assignments/9999/complete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/assignments/{id}/attachment
# ---------------------------------------------------------------------------

class TestAttachment:
    def test_pdf_upload_returns_200_and_file_url(self, client, db_session, monkeypatch):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr("app.config.settings.UPLOAD_DIR", tmp)
            assignment = _seed_assignment(db_session)
            resp = client.post(
                f"/api/assignments/{assignment.id}/attachment",
                files={"file": ("report.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_url"] is not None
        assert data["file_url"].startswith("/uploads/")

    def test_exe_upload_returns_400(self, client, db_session, monkeypatch):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr("app.config.settings.UPLOAD_DIR", tmp)
            assignment = _seed_assignment(db_session)
            resp = client.post(
                f"/api/assignments/{assignment.id}/attachment",
                files={"file": ("malware.exe", io.BytesIO(SAMPLE_EXE), "application/x-msdownload")},
            )
        assert resp.status_code == 400

    def test_attachment_not_found_returns_404(self, client):
        resp = client.post(
            "/api/assignments/9999/attachment",
            files={"file": ("report.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/assignments filters
# ---------------------------------------------------------------------------

class TestListFilters:
    def test_filter_by_type(self, client, db_session):
        course = Course(title="C")
        db_session.add(course)
        db_session.flush()
        a1 = Assignment(title="HW1", course_id=course.id, due_date=date.today(), status="Not started", type="Homework")
        a2 = Assignment(title="Quiz1", course_id=course.id, due_date=date.today(), status="Not started", type="Quiz")
        db_session.add_all([a1, a2])
        db_session.commit()

        resp = client.get("/api/assignments?type=Homework")
        assert resp.status_code == 200
        items = resp.json()
        assert all(a["type"] == "Homework" for a in items)

    def test_filter_by_status(self, client, db_session):
        course = Course(title="C")
        db_session.add(course)
        db_session.flush()
        a1 = Assignment(title="HW1", course_id=course.id, due_date=date.today(), status="Completed")
        a2 = Assignment(title="HW2", course_id=course.id, due_date=date.today(), status="Not started")
        db_session.add_all([a1, a2])
        db_session.commit()

        resp = client.get("/api/assignments?status=Completed")
        assert resp.status_code == 200
        items = resp.json()
        assert all(a["status"] == "Completed" for a in items)

    def test_filter_by_course_id(self, client, db_session):
        c1 = Course(title="C1")
        c2 = Course(title="C2")
        db_session.add_all([c1, c2])
        db_session.flush()
        a1 = Assignment(title="HW1", course_id=c1.id, due_date=date.today(), status="Not started")
        a2 = Assignment(title="HW2", course_id=c2.id, due_date=date.today(), status="Not started")
        db_session.add_all([a1, a2])
        db_session.commit()

        resp = client.get(f"/api/assignments?course_id={c1.id}")
        assert resp.status_code == 200
        items = resp.json()
        assert all(a["course_id"] == c1.id for a in items)

    def test_no_filters_returns_all(self, client, db_session):
        course = Course(title="C")
        db_session.add(course)
        db_session.flush()
        for i in range(3):
            db_session.add(Assignment(title=f"HW{i}", course_id=course.id, due_date=date.today(), status="Not started"))
        db_session.commit()

        resp = client.get("/api/assignments")
        assert resp.status_code == 200
        assert len(resp.json()) >= 3

    def test_combined_filters(self, client, db_session):
        c1 = Course(title="C1")
        c2 = Course(title="C2")
        db_session.add_all([c1, c2])
        db_session.flush()
        a1 = Assignment(title="HW1", course_id=c1.id, due_date=date.today(), status="Completed", type="Homework")
        a2 = Assignment(title="HW2", course_id=c1.id, due_date=date.today(), status="Completed", type="Quiz")
        a3 = Assignment(title="HW3", course_id=c2.id, due_date=date.today(), status="Completed", type="Homework")
        db_session.add_all([a1, a2, a3])
        db_session.commit()

        resp = client.get(f"/api/assignments?course_id={c1.id}&status=Completed&type=Homework")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["title"] == "HW1"