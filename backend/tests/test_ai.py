"""Tests for the AI foundation (Group 1).

Hermetic: every test monkeypatches ``ai_client.ai_available`` so the suite
never touches the network regardless of ``AI_ENABLED``.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.config import settings
from app.services import ai_client, ai_fallback


# ---------------------------------------------------------------------------
# extract_json (Phase 5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('```\n[1, 2, 3]\n```', [1, 2, 3]),
        ('Here is the JSON you asked for:\n{"weeks": [1, 2]} trailing prose', {"weeks": [1, 2]}),
        ('[{"front": "q?", "back": "a"}]', [{"front": "q?", "back": "a"}]),
        ('  \n {"nested": {"deep": [1, {"x": 2}]}} \n ', {"nested": {"deep": [1, {"x": 2}]}}),
    ],
)
def test_extract_json(raw, expected):
    assert ai_client.extract_json(raw) == expected


def test_extract_json_invalid():
    assert ai_client.extract_json(None) is None
    assert ai_client.extract_json("") is None
    assert ai_client.extract_json("no json here") is None
    assert ai_client.extract_json("```json\nnot really\n```") is None


# ---------------------------------------------------------------------------
# Capability endpoints (Phases 3, 7)
# ---------------------------------------------------------------------------

def test_ai_health(client):
    resp = client.get("/api/ai/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert "models" in data
    assert settings.AI_MODEL in data["models"]


def test_ai_models(client):
    resp = client.get("/api/ai/models")
    assert resp.status_code == 200
    data = resp.json()
    assert settings.AI_MODEL in data["models"]
    assert isinstance(data["enabled"], bool)


def test_ai_complete_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/complete", json={"prompt": "Hello there"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_used"] is False
    assert data["text"]


# ---------------------------------------------------------------------------
# Feature endpoints — deterministic fallback paths (Phases 28/29/42/50/57)
# ---------------------------------------------------------------------------

def test_ai_quiz_demo_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/quiz", json={"content": "Some study notes about biology."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_used"] is False
    questions = data["questions"]
    assert len(questions) >= 3
    for q in questions:
        assert q["q"]
        assert len(q["opts"]) >= 2
        assert isinstance(q["ans"], int)


def test_ai_flashcards_demo_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/flashcards", json={"topic": "Biology", "difficulty": "medium"})
    assert resp.status_code == 200
    cards = resp.json()["cards"]
    assert len(cards) >= 2
    for c in cards:
        assert c["front"] and c["back"]


def test_ai_study_plan_demo_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/study-plan", json={"subject": "Calculus Final", "exam_date": "2026-06-01"})
    assert resp.status_code == 200
    plan = resp.json()["plan"]
    assert plan["subject"] == "Calculus Final"
    assert len(plan["weeks"]) == 4
    for w in plan["weeks"]:
        assert w["topic"]
        assert isinstance(w["tasks"], list)


def test_ai_syllabus_demo_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/syllabus", json={"text": "Course syllabus for English 101..."})
    assert resp.status_code == 200
    assignments = resp.json()["assignments"]
    assert len(assignments) >= 3
    for a in assignments:
        assert a["title"]
        assert "due_date" in a


def test_ai_chat_fallback_uses_db_context(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    # Greeting branch should mention the seeded pending assignments.
    resp = client.post("/api/ai/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Hey!" in data["message"]
    assert data["ai_used"] is False
    assert "pending" in data["message"]

    # Deadline branch should list upcoming deadlines.
    resp = client.post("/api/ai/chat", json={"message": "what is due this week?"})
    data = resp.json()
    assert "Upcoming deadlines" in data["message"]

    # Study-plan intent flag
    resp = client.post("/api/ai/chat", json={"message": "generate a study plan"})
    data = resp.json()
    assert data["should_generate_plan"] is True


def test_ai_grade_answer_exact_match(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post(
        "/api/ai/grade-answer",
        json={"question": "What is 2+2?", "expected": "Four", "answer": "four"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["correct"] is True
    assert data["ai_used"] is False

    resp = client.post(
        "/api/ai/grade-answer",
        json={"question": "What is 2+2?", "expected": "Four", "answer": "five"},
    )
    assert resp.json()["correct"] is False
    assert "four" in resp.json()["explanation"].lower()


# ---------------------------------------------------------------------------
# ai_client.generate through the provider registry (Phase 2)
#
# Generation now happens inside ``app.services.ai_providers`` (OpenAI-compatible
# provider via httpx.Client). These tests inject an ``httpx.MockTransport`` and
# drive the real registry path so payload shape + fallback behavior are verified.
# ---------------------------------------------------------------------------

import httpx

from app.services import ai_providers


def _registry_with_transport(monkeypatch, handler, config_overrides=None, tmp_path=None):
    """Point the module registry at a temp file + a mock transport."""
    path = (tmp_path or Path("/tmp")) / f"providers-{uuid.uuid4().hex[:8]}.json"
    reg = ai_providers.ProviderRegistry(path=path)
    base = config_overrides or {}
    reg.create(
        name=base.get("name", "Test Provider"),
        provider_type=base.get("provider_type", "custom"),
        base_url=base.get("base_url", "http://mock.local/v1"),
        api_key=base.get("api_key", settings.AI_API_KEY or "test-key"),
        model=base.get("model", "test-model"),
    )
    monkeypatch.setattr(ai_providers, "get_registry", lambda: reg)
    monkeypatch.setattr(ai_client, "ai_available", lambda: True)

    def _client(config, timeout=ai_providers.DEFAULT_TIMEOUT):
        return httpx.Client(base_url=config.base_url.rstrip("/"), timeout=timeout, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(ai_providers, "_client", _client)
    return reg


def test_generate_success(monkeypatch, tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["json"] = json.loads(request.content or b"{}")
        return httpx.Response(200, json={"choices": [{"message": {"content": "  mock answer  "}}]})

    _registry_with_transport(monkeypatch, handler, tmp_path=tmp_path)
    text = ai_client.generate("hello", model="test-model")
    assert text == "mock answer"
    assert captured["json"]["model"] == "test-model"
    assert captured["url"].endswith("/chat/completions")
    # OmniRoute-style gateways default to SSE streaming; the client parses a
    # single JSON body, so completions must be requested non-streamed.
    assert captured["json"]["stream"] is False
    # httpx normalises header names to lowercase inside MockTransport.
    auth = captured["headers"].get("authorization") or captured["headers"].get("Authorization")
    assert auth == f"Bearer {settings.AI_API_KEY or 'test-key'}"


def test_generate_disabled(monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    assert ai_client.generate("hello") is None


def test_generate_uses_configured_model(monkeypatch, tmp_path):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content or b"{}")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    # No explicit model → the provider's configured model is used.
    _registry_with_transport(monkeypatch, handler, config_overrides={"model": "configured-model"}, tmp_path=tmp_path)
    assert ai_client.generate("hello") == "ok"
    assert captured["json"]["model"] == "configured-model"


def test_generate_returns_none_on_connection_error(monkeypatch, tmp_path):
    def boom(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("connection refused")

    _registry_with_transport(monkeypatch, boom, tmp_path=tmp_path)
    assert ai_client.generate("hello") is None


# ---------------------------------------------------------------------------
# Fallback generators (Phase 4)
# ---------------------------------------------------------------------------

def test_fallback_shapes_are_stable():
    quiz = ai_fallback.demo_quiz("Some content about photosynthesis and cells.")
    assert isinstance(quiz, list) and quiz
    plan = ai_fallback.demo_study_plan("Biology")
    assert plan["weeks"][0]["week"] == 1
    cards = ai_fallback.demo_flashcards("Topic", "hard")
    assert all(c["front"] and c["back"] for c in cards["cards"])
    extracted = ai_fallback.demo_syllabus("English 101 syllabus")
    assert extracted[0]["course"] == "English 101"
    graded = ai_fallback.demo_grade_answer("q", "The answer", "the answer")
    assert graded["correct"] is True
    chat = ai_fallback.local_chat_response("hello", {})
    assert "Hey!" in chat["message"]
