"""Tests for the habits API endpoints."""

import pytest


def test_list_habits(client):
    resp = client.get("/api/habits")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert data[0]["name"] is not None


def test_get_habit(client):
    resp = client.get("/api/habits/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Morning Exercise"


def test_get_habit_not_found(client):
    resp = client.get("/api/habits/9999")
    assert resp.status_code == 404


def test_create_habit(client):
    resp = client.post("/api/habits", json={
        "name": "New Habit",
        "frequency": "daily",
        "target_count": 1,
        "user_id": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Habit"


def test_update_habit(client):
    resp = client.put("/api/habits/1", json={
        "name": "Updated Habit",
        "frequency": "weekly",
        "target_count": 2,
        "user_id": 1,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Habit"


def test_delete_habit(client):
    resp = client.delete("/api/habits/1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_list_habit_logs(client):
    resp = client.get("/api/habits/1/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_create_habit_log(client):
    resp = client.post("/api/habit-logs", json={
        "habit_id": 1,
        "date": "2026-07-29",
        "completed": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    # Verify streak incremented
    habit_resp = client.get("/api/habits/1")
    assert habit_resp.json()["current_streak"] > 3
