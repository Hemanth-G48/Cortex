"""Tests for the courses API endpoints."""

import pytest


def test_list_courses(client):
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    assert data[0]["title"] == "Computer Science"


def test_get_course(client):
    resp = client.get("/api/courses/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["title"] == "Computer Science"


def test_get_course_not_found(client):
    resp = client.get("/api/courses/9999")
    assert resp.status_code == 404


def test_create_course(client):
    resp = client.post("/api/courses/", json={
        "title": "Test Course",
        "current_assignment": 0,
        "total_assignments": 0,
        "total_exams": 0,
        "status": "Not started",
        "user_id": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Course"
    assert data["id"] is not None


def test_update_course(client):
    resp = client.put("/api/courses/1", json={
        "title": "Updated CS",
        "current_assignment": 2,
        "total_assignments": 4,
        "total_exams": 4,
        "status": "Completed",
        "user_id": 1,
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated CS"
    assert resp.json()["status"] == "Completed"


def test_delete_course(client):
    resp = client.delete("/api/courses/1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_delete_course_not_found(client):
    resp = client.delete("/api/courses/9999")
    assert resp.status_code == 404
