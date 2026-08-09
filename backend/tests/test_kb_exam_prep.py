"""Idea 53 — exam prep tests.

Reverse-scheduled daily buckets from the exam date (fallback: +14 days when no
exam/deadline), weak/hard topics weighted first, materialization into Tasks is
idempotent, per-user isolation.
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

## Unit 3: Classification
- Logistic regression
- Decision trees
"""


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="exam-user", email="exam@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Exam", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    confirmed = client.post(
        f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token)
    )
    profile = confirmed.json()["profile"]  # now carries curriculum_subject_id
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


class TestGenerate:
    def test_reverse_schedule_from_exam_date(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep",
            json={},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        prep = r.json()["prep"]
        assert prep["days_left"] >= 1
        assert prep["daily_tasks"]
        # Dates are on/after today and strictly before the exam date.
        for day in prep["daily_tasks"]:
            d = date.fromisoformat(day["date"])
            assert d >= date.today()
            assert d <= date.fromisoformat(prep["exam_date"])

    def test_all_topics_covered(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep", json={}, headers=_auth(token)
        )
        topics = client.get(
            f"/api/subjects/{profile['id']}/topics", headers=_auth(token)
        ).json()["items"]
        covered = [t for day in r.json()["prep"]["daily_tasks"] for t in day["topic_ids"]]
        assert len(covered) == len({c for c in covered}) == len(topics)

    def test_with_explicit_exam(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        exam_date = (date.today() + timedelta(days=10)).isoformat()
        exam = client.post(
            "/api/exams",
            json={"title": "Midterm", "course_id": profile["curriculum_subject_id"],
                  "date": exam_date, "status": "Not started"},
            headers=_auth(token),
        )
        assert exam.status_code in (200, 201), exam.text
        exam_id = exam.json()["id"]
        r = client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep?exam_id={exam_id}",
            json={},
            headers=_auth(token),
        )
        prep = r.json()["prep"]
        assert prep["exam_date"] == exam_date
        assert prep["days_left"] == 10


class TestMaterialize:
    def test_creates_tasks_idempotently(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        r1 = client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep", json={}, headers=_auth(token)
        )
        created = r1.json()["tasks_created"]
        assert created >= 1
        r2 = client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep", json={}, headers=_auth(token)
        )
        assert r2.json()["tasks_created"] == 0  # already materialized
        tasks = db_session.query(Task).filter(Task.title.like("Exam prep%")).all()
        assert len(tasks) == created

    def test_tasks_have_due_dates(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        client.post(f"/api/subjects-ai/{profile['id']}/exam-prep", json={}, headers=_auth(token))
        tasks = db_session.query(Task).filter(Task.title.like("Exam prep%")).all()
        assert tasks
        for t in tasks:
            assert t.due_date is not None
            assert t.priority_tag == "High"


class TestIsolation:
    def test_exam_prep_is_per_user(self, client):
        token_a = _signup(client, "exam-a", "exama@test.com")
        token_b = _signup(client, "exam-b", "examb@test.com")
        profile = _confirmed(client, token_a)
        assert client.get(
            f"/api/subjects-ai/{profile['id']}/exam-prep", headers=_auth(token_b)
        ).status_code == 404
        assert client.post(
            f"/api/subjects-ai/{profile['id']}/exam-prep", json={}, headers=_auth(token_b)
        ).status_code == 404
