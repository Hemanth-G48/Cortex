"""Tests for admin authorization on catalog write endpoints."""
from __future__ import annotations

import pytest
from fastapi import status


def test_student_blocked_from_catalog_writes(client, db_session):
    """A student (non-admin) is blocked from admin-gated catalog writes."""
    # Sign up a student
    resp = client.post("/api/auth/signup", json={
        "name": "Student User",
        "username": "studentuser",
        "email": "student@test.com",
        "password": "secret123",
        "role": "student",
    })
    assert resp.status_code == 201
    student_token = resp.json()["token"]

    # Try to create an institution (admin-only)
    resp2 = client.post(
        "/api/curriculum/institutions",
        json={"name": "Test Inst", "short_name": "TST", "is_active": True},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp2.status_code == 403


def test_student_blocked_from_admin_institution_list(client, db_session):
    """A student is blocked from the admin institutions list."""
    # Sign up a student
    resp = client.post("/api/auth/signup", json={
        "name": "Student User 2",
        "username": "studentuser2",
        "email": "student2@test.com",
        "password": "secret123",
        "role": "student",
    })
    assert resp.status_code == 201
    student_token = resp.json()["token"]

    # Try to list all institutions (admin-only)
    resp2 = client.get(
        "/api/curriculum/institutions/admin/all",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp2.status_code == 403


def test_admin_can_list_institutions(client, db_session):
    """The seeded admin user can access admin institution list."""
    token = client.post("/api/auth/login", json={}).json()["token"]

    resp = client.get(
        "/api/curriculum/institutions/admin/all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200