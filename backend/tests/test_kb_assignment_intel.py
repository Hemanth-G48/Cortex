"""Idea 54 — assignment intelligence tests.

Subtask breakdown (deterministic fallback: 3 equal-split subtasks), spaced due
dates backwards from the deadline, Task + Reminder creation, topic linking by
name overlap, hint chunks degrade to [] with no vault content, per-user
assignment ownership for the /plan endpoint.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import Task

SYLLABUS = """\
# Machine Learning

Fall 2026

## Unit 1: Foundations
- Linear algebra review
- Probability review

## Unit 2: Regression
- Linear regression
- Gradient descent
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="ai-user", email="ai@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Intel", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _assignment(client, token, course_id=None, due_days=7):
    due = (date.today() + timedelta(days=due_days)).isoformat()
    payload = {
        "title": "Linear Regression Report",
        "description": "Write a report on gradient descent for linear regression",
        "due_date": due,
        "time_estimate": 180,
    }
    if course_id is not None:
        payload["course_id"] = course_id
    r = client.post("/api/assignments", json=payload, headers=_auth(token))
    assert r.status_code in (200, 201), r.text
    return r.json()


class TestPlan:
    def test_creates_subtasks_spaced_to_deadline(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        a = _assignment(client, token)
        r = client.post(f"/api/assignments/{a['id']}/plan", json={}, headers=_auth(token))
        assert r.status_code == 200, r.text
        result = r.json()
        assert len(result["subtasks"]) == 3
        # Subtasks are ordered with the last due on the deadline.
        dates = [date.fromisoformat(s["due_date"]) for s in result["subtasks"]]
        assert dates[-1] == date.fromisoformat(a["due_date"])
        assert dates == sorted(dates)
        assert len(result["tasks_created"]) == 3
        assert len(result["reminders_created"]) == 3

    def test_hints_degrade_to_empty_without_vault(self, client):
        token = _signup(client)
        a = _assignment(client, token)
        r = client.post(f"/api/assignments/{a['id']}/plan", json={}, headers=_auth(token))
        assert r.json()["hints"] == []

    def test_links_topics_by_name_overlap(self, client, db_session):
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
        profile = r.json()["profile"]
        confirmed = client.post(
            f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token)
        )
        profile = confirmed.json()["profile"]
        client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
        a = _assignment(client, token, course_id=profile["curriculum_subject_id"])
        r = client.post(f"/api/assignments/{a['id']}/plan", json={}, headers=_auth(token))
        assert r.status_code == 200, r.text
        # "linear regression" topic should match the assignment title.
        topics = client.get(
            f"/api/subjects/{profile['id']}/topics", headers=_auth(token)
        ).json()["items"]
        names = {t["name"].lower() for t in topics}
        assert any("linear regression" in n for n in names)
        assert r.json()["topic_ids"]

    def test_idempotent_task_creation(self, client, db_session):
        token = _signup(client)
        a = _assignment(client, token)
        r1 = client.post(f"/api/assignments/{a['id']}/plan", json={}, headers=_auth(token))
        r2 = client.post(f"/api/assignments/{a['id']}/plan", json={}, headers=_auth(token))
        # Second run reuses the same tasks (no duplicates).
        assert r2.json()["tasks_created"] == r1.json()["tasks_created"]
        tasks = db_session.query(Task).filter(Task.title.like("%step%")).all()
        assert len(tasks) == 3

    def test_unknown_assignment_404(self, client):
        token = _signup(client)
        r = client.post("/api/assignments/9999/plan", json={}, headers=_auth(token))
        assert r.status_code == 404


class TestPlanRequest:
    def test_create_tasks_false(self, client):
        token = _signup(client)
        a = _assignment(client, token)
        r = client.post(
            f"/api/assignments/{a['id']}/plan",
            json={"create_tasks": False, "create_reminders": False},
            headers=_auth(token),
        )
        result = r.json()
        assert result["tasks_created"] == []
        assert result["reminders_created"] == []
        assert len(result["subtasks"]) == 3
