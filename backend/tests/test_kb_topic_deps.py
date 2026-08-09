"""Idea 46 — topic dependency graph tests.

LLM seed, fallback seed, cycle rejection (409), manual add/remove,
topological order.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import Topic, TopicDependency
from app.services.security import decode_bearer_token

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


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="dep-user", email="dep@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Dep", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _confirmed_with_topics(client, token):
    r = client.post("/api/subjects/import", json={"text": SYLLABUS}, headers=_auth(token))
    profile = r.json()["profile"]
    client.post(f"/api/subjects/{profile['id']}/confirm", json={}, headers=_auth(token))
    client.post(f"/api/subjects/{profile['id']}/topics/generate", headers=_auth(token))
    # Re-fetch so curriculum_subject_id reflects the confirmed link.
    profile = client.get(f"/api/subjects/{profile['id']}", headers=_auth(token)).json()
    topics = client.get(f"/api/subjects/{profile['id']}/topics", headers=_auth(token)).json()["items"]
    return profile, {t["name"]: t for t in topics}


class TestSeed:
    def test_fallback_seed_uses_syllabus_order(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        r = client.post(f"/api/subjects/{profile['id']}/dependencies/generate", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["created"] >= 2
        deps = client.get(f"/api/subjects/{profile['id']}/dependencies", headers=_auth(token)).json()
        assert deps["edges"]
        # Fallback links consecutive topics within a unit.
        names = {t["normalized_name"]: t["id"] for t in deps["topics"]}
        assert deps["edges"][0]["prereq_topic_id"] in names.values()

    def test_llm_seed(self, client, monkeypatch):
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        llm = {
            "dependencies": [
                {"topic_a": "Gradient descent", "depends_on": ["Linear algebra review"]},
                {"topic_a": "Logistic regression", "depends_on": ["Linear regression"]},
            ]
        }
        monkeypatch.setattr("app.config.settings.AI_ENABLED", True)
        with patch("app.services.ai_client.generate_json", return_value=llm):
            r = client.post(f"/api/subjects/{profile['id']}/dependencies/generate", headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 2
        deps = client.get(f"/api/subjects/{profile['id']}/dependencies", headers=_auth(token)).json()
        edge_names = {(d["prereq_topic_id"], d["postreq_topic_id"]) for d in deps["edges"]}
        assert (topics["Linear algebra review"]["id"], topics["Gradient descent"]["id"]) in edge_names

    def test_seed_idempotent(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, _ = _confirmed_with_topics(client, token)
        first = client.post(f"/api/subjects/{profile['id']}/dependencies/generate", headers=_auth(token)).json()["created"]
        second = client.post(f"/api/subjects/{profile['id']}/dependencies/generate", headers=_auth(token)).json()["created"]
        assert first > 0
        assert second == 0  # all pairs already present


class TestManualEdges:
    def test_manual_add_and_remove(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        r = client.post(
            f"/api/subjects/{profile['id']}/dependencies",
            json={"prereq_topic_id": topics["Linear algebra review"]["id"],
                  "postreq_topic_id": topics["Decision trees"]["id"]},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        deps = client.get(f"/api/subjects/{profile['id']}/dependencies", headers=_auth(token)).json()
        manual = [d for d in deps["edges"] if d["provenance"] == "manual"]
        assert len(manual) == 1
        r = client.delete(f"/api/subjects/dependencies/{manual[0]['id']}", headers=_auth(token))
        assert r.status_code == 200
        deps = client.get(f"/api/subjects/{profile['id']}/dependencies", headers=_auth(token)).json()
        assert all(d["provenance"] != "manual" for d in deps["edges"])

    def test_cycle_rejected_409(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        a = topics["Linear algebra review"]["id"]
        b = topics["Decision trees"]["id"]
        r1 = client.post(f"/api/subjects/{profile['id']}/dependencies",
                         json={"prereq_topic_id": a, "postreq_topic_id": b}, headers=_auth(token))
        assert r1.status_code == 200
        r2 = client.post(f"/api/subjects/{profile['id']}/dependencies",
                         json={"prereq_topic_id": b, "postreq_topic_id": a}, headers=_auth(token))
        assert r2.status_code == 409

    def test_self_dependency_rejected(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        tid = topics["Bubble sort"]["id"] if "Bubble sort" in topics else next(iter(topics.values()))["id"]
        r = client.post(f"/api/subjects/{profile['id']}/dependencies",
                        json={"prereq_topic_id": tid, "postreq_topic_id": tid}, headers=_auth(token))
        assert r.status_code == 409

    def test_cross_subject_topic_rejected(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        other = Topic(user_id=decode_bearer_token(token)["user_id"],
                      subject_id=profile["curriculum_subject_id"] + 1,
                      name="Foreign", normalized_name="foreign")
        db_session.add(other)
        db_session.commit()
        legit = topics["Linear algebra review"]["id"]
        r = client.post(f"/api/subjects/{profile['id']}/dependencies",
                        json={"prereq_topic_id": other.id, "postreq_topic_id": legit},
                        headers=_auth(token))
        assert r.status_code == 400


class TestTopoOrder:
    def test_topological_order(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        profile, topics = _confirmed_with_topics(client, token)
        from app.services.kb.dependencies import topological_order
        from app.services.security import decode_bearer_token

        ids = [t["id"] for t in topics.values()]
        # manual chain: c depends on b depends on a
        a, b, c = ids[0], ids[1], ids[2]
        client.post(f"/api/subjects/{profile['id']}/dependencies",
                    json={"prereq_topic_id": a, "postreq_topic_id": b}, headers=_auth(token))
        client.post(f"/api/subjects/{profile['id']}/dependencies",
                    json={"prereq_topic_id": b, "postreq_topic_id": c}, headers=_auth(token))
        subject_id = profile["curriculum_subject_id"]
        user_id = decode_bearer_token(token)["user_id"]
        order = topological_order(db_session, user_id, subject_id, ids)
        # prerequisites precede dependents
        assert order.index(a) < order.index(b) < order.index(c)
        # all topics present exactly once
        assert sorted(order) == sorted(ids)

    def test_cycle_in_stored_graph_raises(self, client, monkeypatch, db_session):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        import pytest

        from app.models import Topic, TopicDependency
        from app.services.kb.dependencies import DependencyCycleError, topological_order
        from app.services.security import decode_bearer_token

        token = _signup(client)
        user_id = decode_bearer_token(token)["user_id"]
        t1 = Topic(user_id=user_id, subject_id=1, name="One", normalized_name="one")
        t2 = Topic(user_id=user_id, subject_id=1, name="Two", normalized_name="two")
        db_session.add_all([t1, t2])
        db_session.flush()
        # Insert a cycle directly, bypassing the insert guard (phr. 55 covers
        # the API path; this exercises topological_order's own detection).
        db_session.add_all(
            [
                TopicDependency(user_id=user_id, subject_id=1,
                                prereq_topic_id=t1.id, postreq_topic_id=t2.id),
                TopicDependency(user_id=user_id, subject_id=1,
                                prereq_topic_id=t2.id, postreq_topic_id=t1.id),
            ]
        )
        db_session.commit()
        with pytest.raises(DependencyCycleError):
            topological_order(db_session, user_id, 1, [t1.id, t2.id])
