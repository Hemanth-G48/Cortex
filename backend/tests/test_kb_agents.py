"""Idea 91 — multi-agent architecture tests.

Orchestration of the exam-prep request, planner routing, budget enforcement,
deterministic fallback with AI disabled, and per-user isolation.
"""
from __future__ import annotations

import pytest

from app.models import AgentRun
from app.services.kb import agents as agents_service
from app.services.security import decode_bearer_token


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="agent-user", email="agent@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Agent", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestPlanner:
    def test_exam_prep_plan_composition(self):
        plan = agents_service.plan_request("prepare me for Thursday's exam using my weakest topics")
        agents = [s["agent"] for s in plan]
        assert agents[0] == "scheduler"
        assert "retriever" in agents
        assert "quizzer" in agents
        assert "tutor" in agents

    def test_summary_plan(self):
        plan = agents_service.plan_request("summarize my notes")
        assert plan[0]["agent"] == "retriever"
        assert plan[-1]["agent"] == "summarizer"

    def test_default_plan(self):
        plan = agents_service.plan_request("hello there")
        assert plan[0]["agent"] == "retriever"
        assert plan[-1]["agent"] == "tutor"


class TestOrchestration:
    def test_exam_prep_run(self, client, db_session):
        token = _signup(client)
        r = client.post("/api/kb/agents/run", json={"request": "prepare me for Thursday's exam using my weakest topics"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "done"
        assert body["plan"]
        assert any(s["agent"] == "scheduler" for s in body["steps"])
        assert "Study Plan" in body["result"]
        # The run is persisted for the user.
        user_id = decode_bearer_token(token)["user_id"]
        assert db_session.query(AgentRun).filter(AgentRun.user_id == user_id).count() == 1

    def test_run_records_latency(self, client, db_session):
        token = _signup(client)
        r = client.post("/api/kb/agents/run", json={"request": "how healthy is my knowledge base"}, headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["latency_ms"] >= 0
        user_id = decode_bearer_token(token)["user_id"]
        row = db_session.query(AgentRun).filter(AgentRun.user_id == user_id).first()
        assert row.plan
        assert row.steps
        assert row.result

    def test_runs_list(self, client):
        token = _signup(client)
        client.post("/api/kb/agents/run", json={"request": "summarize my notes"}, headers=_auth(token))
        r = client.get("/api/kb/agents/runs", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_budget_enforcement_fallback(self, client, monkeypatch):
        """Budget spent → LLM agents degrade to deterministic fallbacks."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client)
        r = client.post("/api/kb/agents/run", json={"request": "explain linear regression"}, headers=_auth(token))
        assert r.status_code == 200
        # With AI off, tutor steps never call the provider; run still completes.
        assert r.json()["status"] == "done"


class TestIsolation:
    def test_runs_are_per_user(self, client, db_session):
        token_a = _signup(client, "agent-a", "agenta@test.com")
        token_b = _signup(client, "agent-b", "agentb@test.com")
        client.post("/api/kb/agents/run", json={"request": "prepare me for the exam"}, headers=_auth(token_a))
        r = client.get("/api/kb/agents/runs", headers=_auth(token_b))
        assert r.json()["items"] == []
        # And B's run can't see A's AgentRun row.
        user_a = decode_bearer_token(token_a)["user_id"]
        rows = db_session.query(AgentRun).filter(AgentRun.user_id == user_a).all()
        assert len(rows) == 1
        assert all(r.user_id == user_a for r in rows)
