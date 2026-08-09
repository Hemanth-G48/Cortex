"""Idea 29 — search feedback & learning tests.

Verifies automatic search-event logging, the explicit feedback endpoint,
implicit click tracking, the privacy purge, and per-user isolation.
"""
from __future__ import annotations

import json

from app.models import KbSearchEvent


def _signup(client, uname="ev-user", email="ev@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Ev", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _scan(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"d{i}.md").write_text(text)
    r = client.post(
        "/api/kb/sources",
        json={"name": "V", "root_path": str(root)},
        headers={"Authorization": f"Bearer {token}"},
    )
    src = r.json()
    client.post(f"/api/kb/sources/{src['id']}/scan",
                headers={"Authorization": f"Bearer {token}"})


class TestSearchEvents:
    def test_search_logs_event(self, client, tmp_path, db_session):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Alpha content."])
        client.post(
            "/api/kb/search",
            json={"query": "alpha", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        events = db_session.query(KbSearchEvent).all()
        assert len(events) == 1
        assert events[0].query == "alpha"
        assert events[0].mode == "keyword"

    def test_feedback_endpoint(self, client, tmp_path, db_session):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Beta content."])
        r = client.post(
            "/api/kb/search/feedback",
            json={"query": "beta", "chunk_id": 1, "rating": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        event = db_session.query(KbSearchEvent).filter(
            KbSearchEvent.rating == 1
        ).first()
        assert event is not None
        assert event.query == "beta"

    def test_implicit_click_tracking(self, client, tmp_path, db_session):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Gamma content."])
        r = client.post(
            "/api/kb/search/feedback",
            json={"query": "gamma", "chunk_id": 7, "clicked": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        event = db_session.query(KbSearchEvent).filter(
            KbSearchEvent.clicked_id == 7
        ).first()
        assert event is not None

    def test_privacy_purge(self, client, tmp_path, db_session):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Delta content."])
        client.post(
            "/api/kb/search",
            json={"query": "delta", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/kb/search/feedback",
            json={"query": "delta", "rating": -1},
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.delete(
            "/api/kb/search/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        assert db_session.query(KbSearchEvent).count() == 0

    def test_per_user_isolation(self, client, tmp_path, db_session):
        t1 = _signup(client, "ev-u1", "ev1@test.com")
        t2 = _signup(client, "ev-u2", "ev2@test.com")
        _scan(client, t1, tmp_path, ["Epsilon content."])
        client.post(
            "/api/kb/search",
            json={"query": "epsilon", "mode": "keyword"},
            headers={"Authorization": f"Bearer {t1}"},
        )
        # user2's history is empty.
        r = client.get(
            "/api/kb/search/events",
            headers={"Authorization": f"Bearer {t2}"},
        )
        assert r.json()["total"] == 0
        r1 = client.get(
            "/api/kb/search/events",
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert r1.json()["total"] == 1
