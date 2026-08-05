"""Tests for the Study Plans feature (Groups 6-7)."""
from __future__ import annotations

from app.services import ai_client


def test_seeded_study_plan(client):
    resp = client.get("/api/study-plans")
    assert resp.status_code == 200
    plans = resp.json()
    assert len(plans) >= 1
    assert plans[0]["subject"]
    assert len(plans[0]["weeks"]) == 4


def test_study_plan_crud(client):
    resp = client.post("/api/study-plans", json={
        "subject": "Calculus Final",
        "exam_date": "2026-06-01",
        "weeks": [
            {"week": 1, "topic": "Limits", "tasks": ["Read Ch 1", "Practice problems"]},
            {"week": 2, "topic": "Derivatives", "tasks": ["Read Ch 2", "Past exams"]},
        ],
    })
    assert resp.status_code == 200
    created = resp.json()
    assert created["id"]
    assert created["subject"] == "Calculus Final"
    assert len(created["weeks"]) == 2
    assert created["weeks"][0]["tasks"][0] == "Read Ch 1"

    resp = client.get(f"/api/study-plans/{created['id']}")
    assert resp.json()["weeks"][1]["topic"] == "Derivatives"

    resp = client.delete(f"/api/study-plans/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/study-plans/{created['id']}").status_code == 404


def test_ai_study_plan_endpoint_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/study-plan", json={"subject": "Physics Midterm", "exam_date": "2026-05-20"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_used"] is False
    assert data["plan"]["subject"] == "Physics Midterm"
    assert data["plan"]["exam_date"] == "2026-05-20"
    assert len(data["plan"]["weeks"]) == 4
