"""Tests for curriculum subject endpoints."""
import pytest
from fastapi import status


def get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


def get_student_token(client):
    resp = client.post("/api/auth/signup", json={
        "name": "Student User",
        "email": "student@test.com",
        "password": "password123",
        "role": "student",
    })
    assert resp.status_code == 201
    return resp.json()["token"]


class TestListSubjects:
    def test_lists_subjects_ordered_by_semester(self, client):
        token = get_token(client)
        # Get the BTECH-CSE program id via institution
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        program_id = resp2.json()[0]["id"]

        resp3 = client.get(
            f"/api/curriculum/programs/{program_id}/subjects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
        subjects = resp3.json()
        assert len(subjects) == 5

        # Verify ordered by semester
        semesters = [s["semester"] for s in subjects]
        assert semesters == sorted(semesters)

        # Verify unit_count is present and >= 0
        for s in subjects:
            assert "unit_count" in s
            assert isinstance(s["unit_count"], int)

    def test_unit_count_greater_than_zero_after_seed(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        program_id = resp2.json()[0]["id"]

        resp3 = client.get(
            f"/api/curriculum/programs/{program_id}/subjects",
            headers={"Authorization": f"Bearer {token}"},
        )
        subjects = resp3.json()
        # Each subject should have units from seed
        for s in subjects:
            assert s["unit_count"] > 0, f"Subject {s['name']} has unit_count=0"

    def test_returns_404_for_missing_program(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/programs/99999/subjects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestGetSubject:
    def test_gets_subject(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        program_id = resp2.json()[0]["id"]

        resp3 = client.get(
            f"/api/curriculum/programs/{program_id}/subjects",
            headers={"Authorization": f"Bearer {token}"},
        )
        subject_id = resp3.json()[0]["id"]

        resp4 = client.get(
            f"/api/curriculum/subjects/{subject_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp4.status_code == 200
        data = resp4.json()
        assert data["code"] == "DS"
        assert data["unit_count"] > 0

    def test_returns_404_for_missing(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/subjects/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestAdminCreateSubject:
    def test_creates_subject_under_program(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        program_id = resp2.json()[0]["id"]

        resp3 = client.post(
            f"/api/curriculum/programs/{program_id}/subjects",
            json={
                "name": "Electives",
                "code": "ELECT",
                "semester": 6,
                "credits": 3,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
        data = resp3.json()
        assert data["name"] == "Electives"
        assert data["code"] == "ELECT"
        assert data["unit_count"] == 0

    def test_create_allowed_for_any_user(self, client):
        # Single-user app: curriculum writes are not admin-gated.
        token = get_student_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        program_id = resp2.json()[0]["id"]

        resp3 = client.post(
            f"/api/curriculum/programs/{program_id}/subjects",
            json={"name": "Hacker Subject", "code": "HACK"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
