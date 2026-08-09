"""Idea 95 — QuestLog AI response cache + productivity insights tests.

Covers:
- ``services.ai_cache``: TTL hit/miss, expiry, bounded eviction, disabled mode.
- ``POST /api/ai/insights``: stats bundle from seeded data, deterministic
  fallback when AI is off, cache-first behavior (second call returns the same
  text without re-generating), and cache stats surfaced on /health.

Hermetic: no network. AI availability is monkeypatched to False so the
deterministic fallback runs; cache behavior is exercised by clearing the
singleton between tests.
"""
from __future__ import annotations

import time

import pytest

from app.models import Task, User
from app.services import ai_cache, ai_client
from app.services.ai_insights import build_stats_bundle, get_insights


@pytest.fixture(autouse=True)
def _clean_cache():
    ai_cache.clear_cache()
    yield
    ai_cache.clear_cache()


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)


# ---------------------------------------------------------------------------
# services.ai_cache
# ---------------------------------------------------------------------------


class TestAiCache:
    def test_miss_then_hit(self):
        key = "k1"
        assert ai_cache.cache_stats()["size"] == 0
        assert ai_cache._cache.get(key) is None  # noqa: SLF001 — direct store access

        calls: list[str] = []

        def fake_gen(prompt, **kwargs):  # noqa: ARG001
            calls.append(prompt)
            return "cached-text"

        text, cached = ai_cache.cached_completion("prompt-a", generate=fake_gen)
        assert text == "cached-text"
        assert cached is False
        assert calls == ["prompt-a"]

        # Second call within TTL → served from cache, generate not re-invoked.
        text2, cached2 = ai_cache.cached_completion("prompt-a", generate=fake_gen)
        assert text2 == "cached-text"
        assert cached2 is True
        assert calls == ["prompt-a"]  # still one provider call

    def test_different_prompts_do_not_collide(self):
        def fake_gen(prompt, **kwargs):  # noqa: ARG001
            return f"answer:{prompt}"

        a1, _ = ai_cache.cached_completion("hello", generate=fake_gen)
        a2, _ = ai_cache.cached_completion("world", generate=fake_gen)
        assert a1 == "answer:hello"
        assert a2 == "answer:world"

    def test_ttl_expiry(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_CACHE_TTL_SECONDS", 1)
        ai_cache.clear_cache()
        ai_cache._cache.set("exp", "v")  # noqa: SLF001

        # Rewind the entry's expiry to force a lazy expiry on read.
        entry = ai_cache._cache._store["exp"]  # noqa: SLF001
        entry.expires_at = time.monotonic() - 1

        assert ai_cache._cache.get("exp") is None  # noqa: SLF001 — expired → miss

    def test_disabled_mode(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_CACHE_ENABLED", False)
        ai_cache._cache.set("k", "v")  # noqa: SLF001
        assert ai_cache._cache.get("k") is None  # noqa: SLF001 — always miss

    def test_bounded_eviction(self, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_CACHE_MAX_ENTRIES", 2)
        ai_cache.clear_cache()
        ai_cache._cache.set("a", "1")
        ai_cache._cache.set("b", "2")
        ai_cache._cache.set("c", "3")  # evicts the oldest ("a")
        stats = ai_cache.cache_stats()
        assert stats["size"] == 2
        assert ai_cache._cache.get("a") is None  # noqa: SLF001 — evicted
        assert ai_cache._cache.get("c") == "3"  # noqa: SLF001


# ---------------------------------------------------------------------------
# POST /api/ai/insights
# ---------------------------------------------------------------------------


class TestInsightsEndpoint:
    def test_insights_fallback_with_seed_data(self, client, db_session):
        resp = client.post("/api/ai/insights")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ai_used"] is False
        assert data["cached"] is False
        assert data["insights"]

        # Stats bundle reflects the seeded user + task data.
        stats = data["stats"]
        assert stats["user"]["total_xp"] == 2340
        assert stats["user"]["level"] == 5
        assert stats["tasks"]["total"] > 0
        assert stats["tasks"]["completion_rate"] >= 0
        assert stats["habits"]["total"] >= 3
        assert "upcoming_exams" in stats["exams"]
        assert "upcoming" in stats["assignments"]

    def test_insights_cached_second_call(self, client, monkeypatch):
        # Force AI on with a deterministic generate so both calls would produce
        # the same text — the second must be served from cache without a
        # provider round-trip.
        monkeypatch.setattr(ai_client, "ai_available", lambda: True)
        calls: list[str] = []

        def fake_gen(prompt, **kwargs):  # noqa: ARG001
            calls.append(prompt)
            return "**Your completion rate is looking great!** Keep going."

        monkeypatch.setattr(ai_client, "generate", fake_gen)

        r1 = client.post("/api/ai/insights").json()
        assert r1["ai_used"] is True
        assert r1["cached"] is False
        assert len(calls) == 1

        r2 = client.post("/api/ai/insights").json()
        assert r2["ai_used"] is True
        assert r2["cached"] is True
        assert r2["insights"] == r1["insights"]
        assert len(calls) == 1  # still one provider call — served from cache

    def test_insights_cache_key_includes_stats(self, client, db_session, monkeypatch):
        """Bundle changes (a new task) produce a different cache key → new call."""
        monkeypatch.setattr(ai_client, "ai_available", lambda: True)
        calls: list[str] = []

        def fake_gen(prompt, **kwargs):  # noqa: ARG001
            calls.append(prompt)
            return f"insight {len(calls)}"

        monkeypatch.setattr(ai_client, "generate", fake_gen)

        client.post("/api/ai/insights")
        # Add a pending task → stats change → cache key changes.
        user = db_session.query(User).first()
        db_session.add(Task(title="New urgent task", user_id=user.id, status="Not started"))
        db_session.commit()
        client.post("/api/ai/insights")
        assert len(calls) == 2

    def test_health_surfaces_cache_stats(self, client):
        resp = client.get("/api/ai/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "cache" in data
        assert data["cache"]["enabled"] is True
        assert "size" in data["cache"]
        assert "hits" in data["cache"]
        assert "misses" in data["cache"]


# ---------------------------------------------------------------------------
# services.ai_insights (unit)
# ---------------------------------------------------------------------------


class TestInsightsService:
    def test_build_stats_bundle(self, db_session):
        user = db_session.query(User).first()
        bundle = build_stats_bundle(db_session, user)
        assert bundle["user"]["total_xp"] == user.total_xp
        assert bundle["tasks"]["completed"] >= 0
        assert bundle["habits"]["best_streak"] >= 3  # seed habits have streaks
        assert bundle["assignments"]["pending"] > 0
        assert "upcoming_exams" in bundle["exams"]

    def test_get_insights_fallback_offline(self, db_session):
        user = db_session.query(User).first()
        result = get_insights(db_session, user)
        assert result["ai_used"] is False
        assert result["cached"] is False
        assert "completion" in result["insights"] or "XP" in result["insights"]

    def test_fallback_mentions_real_numbers(self, db_session):
        """The deterministic fallback must cite actual seeded numbers."""
        user = db_session.query(User).first()
        bundle = build_stats_bundle(db_session, user)
        from app.services.ai_insights import _fallback_insights

        out = _fallback_insights(bundle)
        assert (
            str(bundle["tasks"]["completion_rate"]) in out
            or f"{bundle['tasks']['completed']}/{bundle['tasks']['total']}" in out
        )
        assert str(bundle["user"]["total_xp"]) in out
