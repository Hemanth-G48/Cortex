"""Tests for the Analytics feature (Groups 11-12)."""
from __future__ import annotations


def test_analytics_summary(client):
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_focus_minutes" in data
    assert "weekly_focus_minutes" in data
    assert "completion_rate" in data
    assert "gpa" in data
    assert data["total_assignments"] >= 10
    assert data["completed_assignments"] >= 1
    assert data["total_xp"] >= 2000
    assert data["level"] >= 1


def test_analytics_weekly_focus(client):
    resp = client.get("/api/analytics/weekly-focus")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    for w in data:
        assert "week" in w
        assert "minutes" in w
        assert w["minutes"] >= 0


def test_analytics_heatmap(client):
    resp = client.get("/api/analytics/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 52 * 7
    # Seeded pomodoro sessions produce at least one non-zero day.
    assert any(d["minutes"] > 0 for d in data)
