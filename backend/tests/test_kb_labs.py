"""Idea 55 — labs tests.

CRUD per subject+user, status transitions (scheduled → done/missed), completion
logs a ``lab`` LearningEvent per prerequisite topic, prep endpoint degrades to
[] without vault content, per-user isolation.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models import LearningEvent

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


def _signup(client, uname="lab-user", email="lab@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Lab", "username": uname, "email": email,
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
    topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
    return profile, topics


def _create_lab(client, token, subject_id, topic_ids, title="Lab 1"):
    r = client.post(
        f"/api/subjects/{subject_id}/labs",
        json={
            "subject_id": subject_id,
            "title": title,
            "lab_date": (date.today() + timedelta(days=2)).isoformat(),
            "pre_requisite_topic_ids": topic_ids,
        },
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestCrud:
    def test_create_and_list(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        lab = _create_lab(client, token, profile["curriculum_subject_id"], [topics[0]["id"]])
        assert lab["status"] == "scheduled"
        items = client.get(
            f"/api/subjects/{profile['curriculum_subject_id']}/labs", headers=_auth(token)
        ).json()["items"]
        assert len(items) == 1
        assert items[0]["pre_requisite_topic_ids"] == [topics[0]["id"]]

    def test_filter_by_status(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        _create_lab(client, token, profile["curriculum_subject_id"], [topics[0]["id"]])
        client.post(
            f"/api/labs/{_lab_id(client, token, profile)}/complete", headers=_auth(token)
        )
        done = client.get(
            f"/api/subjects/{profile['curriculum_subject_id']}/labs?status=done",
            headers=_auth(token),
        ).json()["items"]
        scheduled = client.get(
            f"/api/subjects/{profile['curriculum_subject_id']}/labs?status=scheduled",
            headers=_auth(token),
        ).json()["items"]
        assert len(done) == 1
        assert len(scheduled) == 0

    def test_update_and_delete(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        lab = _create_lab(client, token, profile["curriculum_subject_id"], [topics[0]["id"]])
        r = client.put(
            f"/api/labs/{lab['id']}",
            json={"title": "Lab 1 Revised", "status": "missed"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Lab 1 Revised"
        assert r.json()["status"] == "missed"
        assert client.delete(f"/api/labs/{lab['id']}", headers=_auth(token)).json()["ok"] is True
        assert client.get(
            f"/api/subjects/{profile['curriculum_subject_id']}/labs", headers=_auth(token)
        ).json()["items"] == []

    def test_invalid_status_400(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        lab = _create_lab(client, token, profile["curriculum_subject_id"], [topics[0]["id"]])
        r = client.put(
            f"/api/labs/{lab['id']}", json={"status": "nonsense"}, headers=_auth(token)
        )
        assert r.status_code == 400


def _lab_id(client, token, profile):
    return client.get(
        f"/api/subjects/{profile['curriculum_subject_id']}/labs", headers=_auth(token)
    ).json()["items"][0]["id"]


class TestCompletion:
    def test_complete_logs_learning_events(self, client, db_session):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        lab = _create_lab(
            client, token, profile["curriculum_subject_id"],
            [topics[0]["id"], topics[1]["id"]],
        )
        r = client.post(f"/api/labs/{lab['id']}/complete", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["status"] == "done"
        events = (
            db_session.query(LearningEvent)
            .filter(LearningEvent.event_type == "lab")
            .all()
        )
        assert len(events) == 2  # one per prerequisite topic
        assert {e.topic_id for e in events} == {topics[0]["id"], topics[1]["id"]}

    def test_prep_degrades_without_vault(self, client):
        token = _signup(client)
        profile, topics = _confirmed(client, token)
        lab = _create_lab(client, token, profile["curriculum_subject_id"], [topics[0]["id"]])
        r = client.get(f"/api/labs/{lab['id']}/prep", headers=_auth(token))
        assert r.status_code == 200
        reading = r.json()["reading"]
        assert len(reading) == 1
        assert reading[0]["topic_id"] == topics[0]["id"]
        assert reading[0]["chunks"] == []  # no vault content


class TestIsolation:
    def test_labs_are_per_user(self, client):
        token_a = _signup(client, "lab-a", "laba@test.com")
        token_b = _signup(client, "lab-b", "labb@test.com")
        profile, topics = _confirmed(client, token_a)
        lab = _create_lab(client, token_a, profile["curriculum_subject_id"], [topics[0]["id"]])
        assert client.put(f"/api/labs/{lab['id']}", json={}, headers=_auth(token_b)).status_code == 404
        assert client.post(f"/api/labs/{lab['id']}/complete", headers=_auth(token_b)).status_code == 404
        assert client.delete(f"/api/labs/{lab['id']}", headers=_auth(token_b)).status_code == 404
        assert client.get(f"/api/labs/{lab['id']}/prep", headers=_auth(token_b)).status_code == 404
