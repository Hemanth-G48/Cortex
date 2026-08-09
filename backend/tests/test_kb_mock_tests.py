"""Idea 64 — mock tests & exam simulations tests.

Covers paper assembly from the subject's grading scheme/topic weights,
reuse of the approved question bank + on-demand generation, the timed runner
with a server-side duration check, per-topic accuracy analytics, history
views, and per-user isolation.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.kb import utcnow

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


def _signup(client, uname="mck-user", email="mck@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mck", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    confirmed = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    profile = confirmed.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    return profile


def _build(client, token, subject_id, **kw):
    r = client.post(
        "/api/kb/mocks/build",
        json={"subject_id": subject_id, **kw},
        headers=_auth(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["mock"]


class TestBuild:
    def test_build_creates_paper_from_topics(self, client):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"],
                      question_count=10, duration_mins=45)
        assert mock["id"] > 0
        assert mock["duration_mins"] == 45
        assert mock["question_count"] >= 3
        assert mock["sections"], "expected section structure"
        assert mock["status"] == "active"

    def test_build_reuses_approved_bank(self, client, db_session):
        from app.models import MockTest
        import json as _json

        token = _signup(client)
        profile = _confirmed(client, token)
        # Approve a question for every topic → they must be reused by the paper.
        topics = client.get(
            f"/api/subjects/{profile['id']}/topics", headers=_auth(token)
        ).json()["items"]
        approved_ids: set[int] = set()
        for t in topics:
            items = client.post(
                "/api/kb/practice/generate",
                json={"topic_id": t["id"], "count": 3, "difficulty": "M"},
                headers=_auth(token),
            ).json()["items"]
            for q in items:
                client.post(f"/api/kb/practice/{q['id']}/approve", headers=_auth(token))
                approved_ids.add(q["id"])

        mock = _build(client, token, profile["curriculum_subject_id"], question_count=10)
        row = db_session.query(MockTest).get(mock["id"])
        structure = _json.loads(row.structure_json)
        paper_ids = {q["id"] for q in structure["questions"]}
        # The paper must reuse approved bank questions (not only generate fresh).
        assert paper_ids & approved_ids, "expected the approved bank to be reused"
        assert mock["question_count"] == len(paper_ids)

    def test_build_no_topics_400(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/mocks/build",
            json={"subject_id": 9999},
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_build_other_users_subject_400(self, client):
        t_a = _signup(client, "mck-a", "mcka@test.com")
        t_b = _signup(client, "mck-b", "mckb@test.com")
        profile_a = _confirmed(client, t_a)
        # B has no topics → cannot build against A's subject id.
        r = client.post(
            "/api/kb/mocks/build",
            json={"subject_id": profile_a["curriculum_subject_id"]},
            headers=_auth(t_b),
        )
        assert r.status_code == 400


class TestRunner:
    def _start(self, client, token, mock_id):
        r = client.post(f"/api/kb/mocks/{mock_id}/start", headers=_auth(token))
        assert r.status_code == 200, r.text
        return r.json()["attempt"]

    def test_submit_scores_and_breaks_down(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"], question_count=6)
        attempt = self._start(client, token, mock["id"])

        # Read the paper structure to answer correctly.
        from app.models import MockTest

        row = db_session.query(MockTest).get(mock["id"])
        structure = __import__("json").loads(row.structure_json)
        answers = {
            q["id"]: q["answer"]
            for q in structure["questions"]
        }
        r = client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": answers},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["score"] == data["total"]
        assert data["percentage"] == 100.0
        assert data["per_topic"], "expected per-topic analytics"
        assert data["late_submission"] is False

    def test_wrong_answers_score_zero(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"], question_count=6)
        attempt = self._start(client, token, mock["id"])

        from app.models import MockTest

        row = db_session.query(MockTest).get(mock["id"])
        structure = __import__("json").loads(row.structure_json)
        wrong = {q["id"]: "definitely not the right answer" for q in structure["questions"]}
        data = client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": wrong},
            headers=_auth(token),
        ).json()
        assert data["score"] == 0
        assert all(b["correct"] == 0 for b in data["per_topic"].values())

    def test_timer_enforced_late_flag(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"],
                      question_count=6, duration_mins=30)
        attempt = self._start(client, token, mock["id"])

        from app.models import MockTestAttempt

        row = db_session.query(MockTestAttempt).get(attempt["id"])
        row.started_at = utcnow() - timedelta(minutes=90)  # way over 30m
        db_session.commit()

        from app.models import MockTest

        mrow = db_session.query(MockTest).get(mock["id"])
        structure = __import__("json").loads(mrow.structure_json)
        answers = {q["id"]: q["answer"] for q in structure["questions"]}
        data = client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": answers},
            headers=_auth(token),
        ).json()
        assert data["late_submission"] is True

    def test_double_submit_400(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"], question_count=6)
        attempt = self._start(client, token, mock["id"])

        from app.models import MockTest

        row = db_session.query(MockTest).get(mock["id"])
        structure = __import__("json").loads(row.structure_json)
        answers = {q["id"]: q["answer"] for q in structure["questions"]}
        ok = client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": answers},
            headers=_auth(token),
        )
        assert ok.status_code == 200
        again = client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": answers},
            headers=_auth(token),
        )
        assert again.status_code == 400

    def test_start_other_users_mock_404(self, client):
        t_a = _signup(client, "mck-c", "mckc@test.com")
        t_b = _signup(client, "mck-d", "mckd@test.com")
        profile_a = _confirmed(client, t_a)
        mock = _build(client, t_a, profile_a["curriculum_subject_id"])
        r = client.post(f"/api/kb/mocks/{mock['id']}/start", headers=_auth(t_b))
        assert r.status_code == 404


class TestHistory:
    def test_history_and_attempts(self, client, db_session):
        token = _signup(client)
        profile = _confirmed(client, token)
        mock = _build(client, token, profile["curriculum_subject_id"], question_count=6)
        attempt = client.post(f"/api/kb/mocks/{mock['id']}/start", headers=_auth(token)).json()["attempt"]
        from app.models import MockTest

        row = db_session.query(MockTest).get(mock["id"])
        structure = __import__("json").loads(row.structure_json)
        answers = {q["id"]: q["answer"] for q in structure["questions"]}
        client.post(
            f"/api/kb/mocks/attempts/{attempt['id']}/submit",
            json={"answers": answers},
            headers=_auth(token),
        )

        mocks = client.get("/api/kb/mocks", headers=_auth(token)).json()["items"]
        assert len(mocks) == 1
        atts = client.get(f"/api/kb/mocks/{mock['id']}/attempts", headers=_auth(token)).json()["items"]
        assert len(atts) == 1
        assert atts[0]["score"] == atts[0]["total"]

    def test_history_is_per_user(self, client):
        t_a = _signup(client, "mck-e", "mcke@test.com")
        t_b = _signup(client, "mck-f", "mckf@test.com")
        profile_a = _confirmed(client, t_a)
        _build(client, t_a, profile_a["curriculum_subject_id"])
        assert client.get("/api/kb/mocks", headers=_auth(t_b)).json()["items"] == []
        assert len(client.get("/api/kb/mocks", headers=_auth(t_a)).json()["items"]) == 1
