"""Tests for curriculum unit endpoints."""
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


class TestListUnits:
    def test_lists_units_ordered_by_unit_number(self, client):
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
            f"/api/curriculum/subjects/{subject_id}/units",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp4.status_code == 200
        units = resp4.json()
        assert len(units) >= 1

        # Verify ordered by unit_number
        numbers = [u["unit_number"] for u in units]
        assert numbers == sorted(numbers)

    def test_returns_404_for_missing_subject(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/subjects/99999/units",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestAdminCreateUnit:
    def test_creates_unit_under_subject(self, client):
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

        resp4 = client.post(
            f"/api/curriculum/subjects/{subject_id}/units",
            json={
                "unit_number": 99,
                "name": "Bonus Unit",
                "description": "An extra unit",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp4.status_code == 200
        data = resp4.json()
        assert data["name"] == "Bonus Unit"
        assert data["unit_number"] == 99

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

        resp3 = client.get(
            f"/api/curriculum/programs/{program_id}/subjects",
            headers={"Authorization": f"Bearer {token}"},
        )
        subject_id = resp3.json()[0]["id"]

        resp4 = client.post(
            f"/api/curriculum/subjects/{subject_id}/units",
            json={"unit_number": 99, "name": "Hacker Unit"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp4.status_code == 200


class TestGetUnit:
    def _first_unit(self, client, token):
        inst_id = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]["id"]
        program_id = client.get(
            f"/api/curriculum/institutions/{inst_id}/programs",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]["id"]
        subject_id = client.get(
            f"/api/curriculum/programs/{program_id}/subjects",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]["id"]
        return client.get(
            f"/api/curriculum/subjects/{subject_id}/units",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]

    def test_returns_single_unit_by_id(self, client):
        token = get_token(client)
        unit = self._first_unit(client, token)
        resp = client.get(
            f"/api/curriculum/units/{unit['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == unit["id"]
        assert resp.json()["name"] == unit["name"]

    def test_returns_404_for_missing_unit(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/units/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
