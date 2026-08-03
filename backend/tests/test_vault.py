"""Integration tests for vault aggregation and related endpoints (Phase 35)."""

import pytest


def test_vault_summary(client):
    resp = client.get("/api/vault/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "overdue_tasks" in data
    assert "completed_today" in data
    assert "total_habits" in data
    assert "active_habits" in data
    assert "current_week_streaks" in data
    assert isinstance(data["current_week_streaks"], list)
    if data["current_week_streaks"]:
        entry = data["current_week_streaks"][0]
        assert "habit" in entry
        assert "streak" in entry


@pytest.mark.parametrize("tab", ["today", "unrelated", "this_week", "inbox", "completed"])
def test_vault_tasks_tabs(client, tab):
    resp = client.get(f"/api/vault/tasks?tab={tab}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_vault_calendar(client):
    resp = client.get("/api/vault/calendar")
    assert resp.status_code == 200
    data = resp.json()
    assert "start" in data
    assert "end" in data
    assert "days" in data
    assert len(data["days"]) == 7
    day = data["days"][0]
    assert "date" in day
    assert "day_of_week" in day
    assert "label" in day
    assert "tasks" in day
    assert "schedule" in day
    assert "deadlines" in day


def test_vault_database(client):
    resp = client.get("/api/vault/database")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("users", "habits", "tasks", "projects", "goals", "logs"):
        assert key in data
        assert isinstance(data[key], int)
        assert data[key] >= 0


def test_habit_heatmap(client):
    resp = client.get("/api/habits/1/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "days" in data
    assert len(data["days"]) == 30
    day = data["days"][0]
    assert "date" in day
    assert "completed" in day
    assert "count" in day


def test_habit_stats(client):
    resp = client.get("/api/habits/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "records_this_month" in data
    assert "days_missed" in data
    assert "days_in_month" in data
    assert "is_new_record" in data
    assert "streak_graph" in data
    assert len(data["streak_graph"]) == 30
    point = data["streak_graph"][0]
    assert "date" in point
    assert "streak_length" in point


def test_project_summary(client):
    resp = client.get("/api/projects/1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert "incomplete_tasks" in data
    assert "days_to_go" in data
    assert "deadline_status" in data


def test_project_task_partial_toggle(client):
    """Regression: the vault task toggle sends only {completed, project_id} and
    must not 422 (ProjectTaskUpdate is all-optional)."""
    resp = client.put("/api/project-tasks/1", json={"completed": True, "project_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is True
    assert data["title"] == "Design database schema"


def test_vault_summary_includes_overdue_last_week(client):
    """Regression: VaultSummary exposes overdue_last_week for the PerformanceWidget."""
    resp = client.get("/api/vault/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "overdue_last_week" in data
    assert isinstance(data["overdue_last_week"], int)
    assert data["overdue_last_week"] >= 0
