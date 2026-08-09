"""AI response cache — QuestLog's ``ai.controller.js`` NodeCache pattern.

QuestLog caches AI responses with a 10-minute TTL (``new NodeCache({ stdTTL:
600, checkperiod: 120 })``) and serves the cached text for identical prompts,
saving provider calls and latency on repeated requests (dashboard insights,
recurring study tips). This module is the FastAPI/SQLAlchemy adaptation:

- thread-safe in-memory store with per-entry TTL + lazy expiry sweep
- bounded: ``AI_CACHE_MAX_ENTRIES`` evicts the oldest entry when full
- master switch ``AI_CACHE_ENABLED`` — when False every call misses, so CI and
  deterministic fallback tests never rely on shared cache state
- ``stats()`` exposes hits/misses/size so ``GET /api/ai/health`` can mirror
  QuestLog's ``getAIStatus`` (which returns ``cacheSize``)

Cache keys are hash digests of the *full* prompt + model + generation
parameters. Because every prompt builder in this app already embeds per-user
context (assignments, courses, memory blocks, retrieval chunks), a key is
effectively per-user — no cross-user leakage.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable

from app.config import settings


class _Entry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: str, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at


class AiResponseCache:
    """Bounded, TTL'd, thread-safe in-memory string cache (QuestLog pattern)."""

    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ── public API ─────────────────────────────────────────────────────── #
    def get(self, key: str) -> str | None:
        """Return the cached value for ``key``, or None on miss/expiry."""
        if not settings.AI_CACHE_ENABLED:
            self._misses += 1
            return None
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at <= time.monotonic():
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: str) -> None:
        """Store ``value`` for ``key`` with the configured TTL."""
        if not settings.AI_CACHE_ENABLED or value is None:
            return
        ttl = max(1, int(settings.AI_CACHE_TTL_SECONDS))
        with self._lock:
            if (
                len(self._store) >= settings.AI_CACHE_MAX_ENTRIES
                and key not in self._store
            ):
                self._evict_oldest_locked()
            self._store[key] = _Entry(value, time.monotonic() + ttl)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            return {
                "size": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "enabled": bool(settings.AI_CACHE_ENABLED),
                "ttl_seconds": max(1, int(settings.AI_CACHE_TTL_SECONDS)),
            }

    # ── internals ──────────────────────────────────────────────────────── #
    def _evict_oldest_locked(self) -> None:
        """Drop the single soonest-to-expire entry (LRU-by-expiry)."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
        del self._store[oldest_key]


# Singleton shared across requests (mirrors QuestLog's module-level NodeCache).
_cache = AiResponseCache()


def cache_key(prompt: str, *, model: str | None = None, max_tokens: int = 2048, temperature: float = 0.7) -> str:
    """Deterministic key for a prompt + generation parameters."""
    raw = f"{model or ''}|{max_tokens}|{temperature}|{prompt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cached_completion(
    prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    generate: Callable[..., str | None],
) -> tuple[str | None, bool]:
    """Serve ``generate(prompt, ...)`` through the cache.

    Returns ``(text, cached)`` — ``cached=True`` when the text came from the
    store. ``generate`` is only invoked on a miss.
    """
    key = cache_key(prompt, model=model, max_tokens=max_tokens, temperature=temperature)
    hit = _cache.get(key)
    if hit is not None:
        return hit, True
    text = generate(prompt, max_tokens=max_tokens, temperature=temperature, model=model)
    if text:
        _cache.set(key, text)
    return text, False


def cache_stats() -> dict:
    """Public stats mirroring QuestLog's ``getAIStatus`` cacheSize block."""
    return _cache.stats()


def clear_cache() -> None:
    _cache.clear()


__all__ = [
    "AiResponseCache",
    "cache_key",
    "cached_completion",
    "cache_stats",
    "clear_cache",
]
