"""Idea 41 — automatic subject creation tests.

Propose, confirm (writes curriculum rows), reject, semester on confirm,
per-user isolation.
"""
from __future__ import annotations

from app.models import CurriculumSubject, CurriculumUnit, SubjectProfile
from app.services.security import decode_bearer_token

SAMPLE_SYLLABUS = """\
# Data Structures

Fall 2026 · 3 credits
Grading: Midterm 30%, Final 40%, Assignments 30%

## Unit 1: Arrays & Lists
- Introduction to arrays
- Linked lists
1. Analyze the time complexity of array operations

## Unit 2: Trees
- Binary trees
- Tree traversal
- Balanced trees
Upon completion, students will be able to implement balanced trees.

Midterm — Mar 10
Final — May 20
"""


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="subject-user", email="subject@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Subject", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _propose(client, token):
    r = client.post("/api/subjects/import", json={"text": SAMPLE_SYLLABUS}, headers=_auth(token))
    assert r.status_code == 200, r.text
    return r.json()["profile"]


class TestPropose:
    def test_import_creates_proposal(self, client, db_session):
        token = _signup(client)
        # Review-before-write: proposing must not add any curriculum rows.
        before_subjects = db_session.query(CurriculumSubject).count()
        before_units = db_session.query(CurriculumUnit).count()
        profile = _propose(client, token)
        assert profile["status"] == "proposed"
        assert profile["semester"] == "Fall 2026"
        assert profile["curriculum_subject_id"] is None
        assert len(profile["parsed"]["units"]) == 2
        assert db_session.query(CurriculumSubject).count() == before_subjects
        assert db_session.query(CurriculumUnit).count() == before_units

    def test_import_requires_text(self, client):
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": ""}, headers=_auth(token))
        assert r.status_code == 400

    def test_proposals_list(self, client):
        token = _signup(client)
        _propose(client, token)
        r = client.get("/api/subjects/proposals", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["status"] == "proposed"


class TestConfirm:
    def test_confirm_writes_curriculum_rows(self, client, db_session):
        token = _signup(client)
        profile = _propose(client, token)
        r = client.post(
            f"/api/subjects/{profile['id']}/confirm",
            json={"name": "Data Structures", "code": "CS201", "credits": 4},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        subject = db_session.query(CurriculumSubject).filter_by(code="CS201").first()
        assert subject is not None
        assert subject.name == "Data Structures"
        assert subject.credits == 4
        units = db_session.query(CurriculumUnit).filter_by(subject_id=subject.id).all()
        assert len(units) == 2
        assert all(u.semester == "Fall 2026" for u in units)
        linked = db_session.query(SubjectProfile).get(profile["id"])
        assert linked.status == "confirmed"
        assert linked.curriculum_subject_id == subject.id

    def test_confirm_uses_parsed_title_default(self, client, db_session):
        token = _signup(client)
        profile = _propose(client, token)
        r = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
        assert r.status_code == 200, r.text
        subject = db_session.query(CurriculumSubject).order_by(CurriculumSubject.id.desc()).first()
        assert subject.name == "Data Structures"
        assert subject.credits == 3  # from parsed_json

    def test_confirm_only_once(self, client):
        token = _signup(client)
        profile = _propose(client, token)
        client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
        r = client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
        assert r.status_code == 400

    def test_reject(self, client, db_session):
        token = _signup(client)
        profile = _propose(client, token)
        before_subjects = db_session.query(CurriculumSubject).count()
        r = client.post(f"/api/subjects/{profile['id']}/reject", headers=_auth(token))
        assert r.status_code == 200
        assert db_session.query(SubjectProfile).get(profile["id"]).status == "rejected"
        assert db_session.query(CurriculumSubject).count() == before_subjects


class TestIsolation:
    def test_per_user_isolation(self, client):
        token_a = _signup(client, "sub-a", "suba@test.com")
        token_b = _signup(client, "sub-b", "subb@test.com")
        profile = _propose(client, token_a)
        # User B cannot see, confirm, or reject A's proposal.
        assert client.get("/api/subjects/proposals", headers=_auth(token_b)).json()["total"] == 0
        assert client.get(f"/api/subjects/{profile['id']}", headers=_auth(token_b)).status_code == 404
        assert client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token_b)).status_code == 404
        assert client.post(f"/api/subjects/{profile['id']}/reject", headers=_auth(token_b)).status_code == 404

    def test_subject_list_semester_filter(self, client):
        token = _signup(client)
        profile = _propose(client, token)
        r = client.get("/api/subjects?semester=Fall", headers=_auth(token))
        assert r.json()["total"] == 1
        r2 = client.get("/api/subjects?semester=Spring", headers=_auth(token))
        assert r2.json()["total"] == 0
        assert r2.json()["items"] == []
