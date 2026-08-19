"""Tests for curriculum institution endpoints."""
import pytest
from fastapi import status


def get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


def get_student_token(client):
    """Create a student user and return their token."""
    resp = client.post("/api/auth/signup", json={
        "name": "Student User",
        "email": "student@test.com",
        "password": "password123",
        "role": "student",
    })
    assert resp.status_code == 201
    return resp.json()["token"]


class TestGetActiveInstitutions:
    def test_lists_active_institutions(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(inst.get("is_active") is True for inst in data)
        assert any(inst["short_name"] == "GLA" for inst in data)

    def test_returns_active_only(self, client, db_session):
        from app.models import Institution
        from sqlalchemy import func
        # Add an inactive institution
        inactive = Institution(name="Inactive Uni", short_name="INACT", is_active=False)
        db_session.add(inactive)
        db_session.commit()

        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        names = [inst["short_name"] for inst in resp.json()]
        assert "INACT" not in names
        assert "GLA" in names


class TestGetInstitutionById:
    def test_gets_institution(self, client):
        token = get_token(client)
        # First get the list to find the GLA id
        resp = client.get(
            "/api/curriculum/institutions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        institutions = resp.json()
        assert len(institutions) >= 1
        inst_id = institutions[0]["id"]

        resp2 = client.get(
            f"/api/curriculum/institutions/{inst_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["short_name"] == "GLA"

    def test_returns_404_for_missing(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestAdminInstitutionEndpoints:
    def test_list_all_includes_inactive(self, client):
        token = get_token(client)
        resp = client.get(
            "/api/curriculum/institutions/admin/all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # Should include GLA (active)
        names = [inst["short_name"] for inst in resp.json()]
        assert "GLA" in names

    def test_create_institution(self, client):
        token = get_token(client)
        resp = client.post(
            "/api/curriculum/institutions",
            json={"name": "New University", "short_name": "NU", "description": "A new uni"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New University"
        assert data["short_name"] == "NU"
        assert data["is_active"] is False  # default is inactive

    def test_toggle_status(self, client):
        token = get_token(client)
        # Create an institution first
        resp = client.post(
            "/api/curriculum/institutions",
            json={"name": "Toggle Uni", "short_name": "TGL"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        inst_id = resp.json()["id"]

        # Toggle to active
        resp2 = client.patch(
            f"/api/curriculum/institutions/{inst_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is True

        # Toggle back to inactive
        resp3 = client.patch(
            f"/api/curriculum/institutions/{inst_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
        assert resp3.json()["is_active"] is False

    def test_owner_manages_institutions(self, client):
        """Single-user app: no admin role gate — the owner manages the catalog."""
        token = get_student_token(client)
        resp = client.get(
            "/api/curriculum/institutions/admin/all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        resp2 = client.post(
            "/api/curriculum/institutions",
            json={"name": "Owner Uni", "short_name": "OWN"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        inst_id = resp2.json()["id"]

        resp3 = client.patch(
            f"/api/curriculum/institutions/{inst_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.status_code == 200
        assert resp3.json()["is_active"] is True
