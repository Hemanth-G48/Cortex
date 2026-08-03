"""Tests for the tasks, reminders, and schedule API endpoints."""

import pytest


class TestTasks:
    def test_list_tasks(self, client):
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        assert data[0]["title"] is not None

    def test_delete_task_not_found(self, client):
        resp = client.delete("/api/tasks/9999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Task not found"

    def test_create_task(self, client):
        resp = client.post("/api/tasks", json={
            "title": "New task",
            "subject_tag": "Test",
            "priority_tag": "High",
            "status": "Not started",
            "user_id": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New task"
        assert data["id"] is not None

    def test_update_task(self, client):
        resp = client.put("/api/tasks/1", json={
            "title": "Updated task",
            "subject_tag": "CS",
            "priority_tag": "Low",
            "status": "Completed",
            "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"

    def test_delete_task(self, client):
        resp = client.delete("/api/tasks/1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestReminders:
    def test_list_reminders(self, client):
        resp = client.get("/api/reminders")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_reminder(self, client):
        resp = client.post("/api/reminders", json={
            "title": "Test reminder",
            "date": "2026-07-30",
            "time": "14:00:00",
            "is_completed": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test reminder"


class TestSchedule:
    def test_list_schedule(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_create_schedule_entry(self, client):
        resp = client.post("/api/schedule", json={
            "user_id": 1,
            "title": "Study Session",
            "day_of_week": 6,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "color": "#ff0000",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["day_of_week"] == 6
