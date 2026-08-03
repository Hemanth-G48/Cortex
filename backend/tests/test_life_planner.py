"""Integration tests for the Life Planner endpoints (Life OS Group 2)."""

import datetime


# ---------------------------------------------------------------------------
# Daily logs (Phase 6)
# ---------------------------------------------------------------------------
class TestDailyLogs:
    def test_list_daily_logs(self, client):
        resp = client.get("/api/daily-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 7
        entry = data[0]
        assert "date" in entry
        assert "time_focused" in entry
        assert "status" in entry

    def test_create_daily_log(self, client):
        today = datetime.date.today().isoformat()
        resp = client.post("/api/daily-logs", json={
            "user_id": 1, "date": today, "time_focused": 75, "status": "active",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["time_focused"] == 75

    def test_upsert_is_idempotent(self, client):
        today = datetime.date.today().isoformat()
        first = client.post("/api/daily-logs", json={
            "user_id": 1, "date": today, "time_focused": 30, "status": "active",
        }).json()
        second = client.post("/api/daily-logs", json={
            "user_id": 1, "date": today, "time_focused": 90, "status": "active",
        }).json()
        assert first["id"] == second["id"]
        assert second["time_focused"] == 90

    def test_update_daily_log(self, client):
        resp = client.put("/api/daily-logs/1", json={"time_focused": 120})
        assert resp.status_code == 200
        assert resp.json()["time_focused"] == 120

    def test_delete_daily_log(self, client):
        resp = client.delete("/api/daily-logs/1")
        assert resp.status_code == 200
        assert len(client.get("/api/daily-logs").json()) == 6

    def test_daily_log_stats(self, client):
        resp = client.get("/api/daily-logs/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_focused_minutes" in data
        assert "days_active_this_month" in data
        assert "days_in_month" in data
        assert data["total_focused_minutes"] >= 0

    def test_update_not_found(self, client):
        resp = client.put("/api/daily-logs/9999", json={"time_focused": 10})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Events (Phase 7)
# ---------------------------------------------------------------------------
class TestEvents:
    def test_list_events(self, client):
        resp = client.get("/api/events")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert "location" in data[0]
        assert "is_completed" in data[0]

    def test_events_today(self, client):
        resp = client.get("/api/events/today")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["date"] == datetime.date.today().isoformat() for e in data)

    def test_create_event(self, client):
        resp = client.post("/api/events", json={
            "user_id": 1, "title": "Coffee with Priya",
            "date": datetime.date.today().isoformat(), "time": "15:30:00",
            "location": "Starbucks", "is_completed": False,
        })
        assert resp.status_code == 200
        assert resp.json()["location"] == "Starbucks"

    def test_update_event(self, client):
        resp = client.put("/api/events/1", json={"is_completed": True})
        assert resp.status_code == 200
        assert resp.json()["is_completed"] is True

    def test_delete_event(self, client):
        resp = client.delete("/api/events/1")
        assert resp.status_code == 200
        assert len(client.get("/api/events").json()) == 4

    def test_event_not_found(self, client):
        resp = client.put("/api/events/9999", json={"is_completed": True})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Life planner summary (Phase 8)
# ---------------------------------------------------------------------------
class TestLifePlannerSummary:
    def test_summary_shape(self, client):
        resp = client.get("/api/life-planner/summary")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("current_streak", "longest_streak", "daily_log_today",
                    "tasks_due_today", "habits_active", "goals_active",
                    "life_area_progress"):
            assert key in data
        assert isinstance(data["current_streak"], int)
        assert "time_focused" in data["daily_log_today"]
        assert isinstance(data["life_area_progress"], list)


# ---------------------------------------------------------------------------
# Eisenhower matrix (Phase 9)
# ---------------------------------------------------------------------------
class TestEisenhower:
    def test_matrix_shape(self, client):
        resp = client.get("/api/eisenhower/matrix")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("urgent_important", "important_not_urgent",
                    "urgent_not_important", "not_important"):
            assert key in data
            assert isinstance(data[key], list)

    def test_matrix_contains_seeded_quadrants(self, client):
        data = client.get("/api/eisenhower/matrix").json()
        # Seeded High-priority tasks are Urgent/Important; Medium are Important/Not Urgent.
        assert len(data["urgent_important"]) >= 3
        assert len(data["important_not_urgent"]) >= 2

    def test_complete_task(self, client):
        # Grab an urgent/important task id from the matrix.
        matrix = client.get("/api/eisenhower/matrix").json()
        task_id = matrix["urgent_important"][0]["id"]
        resp = client.post(f"/api/eisenhower/tasks/{task_id}/complete")
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"

    def test_complete_task_moves_out_of_matrix(self, client):
        matrix = client.get("/api/eisenhower/matrix").json()
        before = len(matrix["urgent_important"])
        task_id = matrix["urgent_important"][0]["id"]
        client.post(f"/api/eisenhower/tasks/{task_id}/complete")
        after = client.get("/api/eisenhower/matrix").json()["urgent_important"]
        assert len(after) == before - 1

    def test_complete_not_found(self, client):
        resp = client.post("/api/eisenhower/tasks/9999/complete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Quick tasks (Phase 10)
# ---------------------------------------------------------------------------
class TestQuickTasks:
    def test_quick_tasks_has_types(self, client):
        resp = client.get("/api/quick-tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all(item["type"] in ("reminder", "task", "event") for item in data)

    def test_quick_tasks_sorted_by_time(self, client):
        data = client.get("/api/quick-tasks").json()
        times = [item["time"] or "23:59:59" for item in data]
        assert times == sorted(times)
        # Timed items must appear before untimed ones.
        timed = [item for item in data if item["time"] is not None]
        untimed = [item for item in data if item["time"] is None]
        if timed and untimed:
            assert data.index(timed[0]) < data.index(untimed[0])


# ---------------------------------------------------------------------------
# Life area goals (Phase 11)
# ---------------------------------------------------------------------------
class TestLifeAreaGoals:
    def test_area_goals(self, client):
        resp = client.get("/api/life-areas/1/goals")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_area_goals_not_found(self, client):
        resp = client.get("/api/life-areas/9999/goals")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task priority_quadrant (Phase 1) exposed via tasks router
# ---------------------------------------------------------------------------
class TestPriorityQuadrant:
    def test_tasks_expose_quadrant(self, client):
        data = client.get("/api/tasks").json()
        assert any(t.get("priority_quadrant") for t in data)

    def test_create_task_with_quadrant(self, client):
        resp = client.post("/api/tasks", json={
            "title": "Quadrant task", "user_id": 1,
            "priority_quadrant": "Urgent/Important",
        })
        assert resp.status_code == 200
        assert resp.json()["priority_quadrant"] == "Urgent/Important"


# ---------------------------------------------------------------------------
# Schedule events expose event_type + location (Phase 2)
# ---------------------------------------------------------------------------
class TestScheduleEventFields:
    def test_schedule_events_expose_fields(self, client):
        data = client.get("/api/schedule").json()
        assert any(e.get("location") for e in data)
        assert any(e.get("event_type") for e in data)
