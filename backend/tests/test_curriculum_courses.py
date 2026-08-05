"""Tests for curriculum program (course) endpoints."""
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


class TestListPrograms:
    def test_lists_active_programs_under_institution(self, client):
        token = get_token(client)
        # Find the GLA institution id
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        institutions = resp.json()
        assert len(institutions) >= 1
        inst_id = institutions[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        programs = resp2.json()
        assert isinstance(programs, list)
        assert len(programs) >= 1
        assert all(p.get("is_active") is True for p in programs)
        assert any(p["code"] == "BTECH-CSE" for p in programs)

    def test_returns_404_for_missing_institution(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions/99999/programs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestGetProgram:
    def test_gets_program(self, client):
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
            f"/api/curriculum/programs/{program_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
        assert resp3.json()["code"] == "BTECH-CSE"

    def test_returns_404_for_missing_program(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/programs/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestAdminCreateProgram:
    def test_creates_program_under_institution(self, client):
        token = get_token(client)
        # Get institution id
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.post(
            f"/api/curriculum/institutions/{inst_id}/programs",
            json={
                "name": "B.Tech ECE",
                "code": "BTECH-ECE",
                "description": "Electronics and Communication",
                "duration": 4,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["name"] == "B.Tech ECE"
        assert data["code"] == "BTECH-ECE"
        assert data["institution_id"] == inst_id

    def test_non_admin_blocked(self, client):
        token = get_student_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        inst_id = resp.json()[0]["id"]

        resp2 = client.post(
            f"/api/curriculum/institutions/{inst_id}/programs",
            json={"name": "Hacker Program", "code": "HACK"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 403
