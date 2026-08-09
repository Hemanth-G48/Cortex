"""Idea 52 — revision scheduling (FSRS) tests.

The scheduler is the vendored py-fsrs engine (``app/services/fsrs``, MIT) run
with empty learn/relearn steps and fuzzing disabled, so intervals are exact:

- A brand-new topic graded 5 (Easy) gets interval 8 days (initial stability
  8.2956 → ``_next_interval``), state Review.
- Grading again grows the interval; a failure-grade (0–1, Again) resets the
  repetition counter and shrinks the legacy ease indicator.

Also covered: due queue, idempotent materialization into the daily schedule,
per-user isolation, and the 422/404 guard rails.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import DailyScheduleItem, RevisionSchedule

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

# Deterministic FSRS: first Easy review of a fresh card (stability 8.2956).
EASY_FIRST_INTERVAL = 8


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="rev-user", email="rev@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Rev", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _first_topic(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    topic = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"][0]
    return profile, topic


class TestFsrs:
    def test_good_grade_schedules_future_review(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token)
        )
        assert r.status_code == 200, r.text
        s1 = r.json()["schedule"]
        assert s1["interval_days"] == EASY_FIRST_INTERVAL  # FSRS, deterministic
        assert s1["repetitions"] == 1
        assert s1["state"] == 2  # Review
        assert s1["stability"] is not None and s1["stability"] > 0
        assert s1["due_date"] > date.today().isoformat()

        # Second review grows the interval further (short-term stability bump).
        r = client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token)
        )
        s2 = r.json()["schedule"]
        assert s2["interval_days"] > s1["interval_days"]
        assert s2["repetitions"] == 2

    def test_failure_grade_resets_repetitions(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        client.post(f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token))
        r = client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 1}, headers=_auth(token)
        )
        s = r.json()["schedule"]
        assert s["repetitions"] == 0  # Again resets the counter
        assert s["ease"] < 2.5  # legacy ease indicator shrinks on failure

    def test_fresh_hard_review_is_short(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 2}, headers=_auth(token)
        )
        assert r.status_code == 200
        # Hard first review → stability 1.2931 → ~1 day interval.
        assert r.json()["schedule"]["interval_days"] == 1

    def test_grade_out_of_range_422(self, client):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        r = client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 9}, headers=_auth(token)
        )
        assert r.status_code == 422

    def test_review_on_unknown_topic_404(self, client):
        token = _signup(client)
        r = client.post("/api/topics/9999/review", json={"grade": 5}, headers=_auth(token))
        assert r.status_code == 404


class TestDueQueue:
    def _force_due(self, db_session, topic_id, days_back=1):
        rs = (
            db_session.query(RevisionSchedule)
            .filter(RevisionSchedule.topic_id == topic_id)
            .first()
        )
        assert rs is not None
        rs.due_date = date.today() - timedelta(days=days_back)
        db_session.commit()

    def test_not_due_until_interval_elapses(self, client, db_session):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token)
        )
        items = client.get("/api/reviews/due", headers=_auth(token)).json()["items"]
        assert all(i["topic_id"] != topic["id"] for i in items)

        # Backdate → appears in the due queue with its schedule state.
        self._force_due(db_session, topic["id"])
        items = client.get("/api/reviews/due", headers=_auth(token)).json()["items"]
        assert len(items) == 1
        assert items[0]["topic_id"] == topic["id"]
        assert items[0]["interval_days"] == EASY_FIRST_INTERVAL
        assert items[0]["repetitions"] == 1

    def test_materialize_is_idempotent(self, client, db_session):
        token = _signup(client)
        _, topic = _first_topic(client, token)
        # Enter the topic into the schedule first (review), then force it due.
        client.post(
            f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token)
        )
        self._force_due(db_session, topic["id"])

        r1 = client.post("/api/reviews/materialize", headers=_auth(token))
        assert r1.status_code == 200
        assert r1.json()["materialized"] == 1
        # Second call skips the already-created schedule block.
        r2 = client.post("/api/reviews/materialize", headers=_auth(token))
        assert r2.json()["materialized"] == 0

        from app.services.security import decode_bearer_token

        user_id = decode_bearer_token(token)["user_id"]
        items = (
            db_session.query(DailyScheduleItem)
            .filter(
                DailyScheduleItem.user_id == user_id,
                DailyScheduleItem.activity.like("Review:%"),
            )
            .all()
        )
        assert len(items) == 1


class TestIsolation:
    def test_review_queue_is_per_user(self, client, db_session):
        from app.models import RevisionSchedule
        from app.services.security import decode_bearer_token

        token_a = _signup(client, "rev-a", "reva@test.com")
        token_b = _signup(client, "rev-b", "revb@test.com")
        _, topic = _first_topic(client, token_a)
        client.post(f"/api/topics/{topic['id']}/review", json={"grade": 5}, headers=_auth(token_a))
        # B has no schedule at all → empty due queue.
        user_b_id = decode_bearer_token(token_b)["user_id"]
        rs_b = (
            db_session.query(RevisionSchedule)
            .filter(RevisionSchedule.user_id == user_b_id)
            .first()
        )
        assert rs_b is None
        assert client.get("/api/reviews/due", headers=_auth(token_b)).json()["items"] == []
        # A's queue is non-empty once due.
        rs_a = (
            db_session.query(RevisionSchedule)
            .filter(RevisionSchedule.topic_id == topic["id"])
            .first()
        )
        rs_a.due_date = date.today() - timedelta(days=1)
        db_session.commit()
        assert len(client.get("/api/reviews/due", headers=_auth(token_a)).json()["items"]) == 1
