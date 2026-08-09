"""Idea 11 — Embeddings service tests.

Verifies the OpenAI-compatible client, the deterministic local fallback, the
dimension normalization, and the per-user daily budget meter. AI_ENABLED=false
short-circuits every provider path (hermetic tests never hit the network).
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.models import KbDocument, KbEmbedding, User
from app.services import embeddings


@pytest.fixture(scope="function")
def kb_user(db_session) -> User:
    user = User(name="E", username="embed", email="embed@test.com", role="student")
    db_session.add(user)
    db_session.flush()
    return user


class TestLocalEmbed:
    def test_deterministic(self):
        a = embeddings.local_embed(["hello world"])
        b = embeddings.local_embed(["hello world"])
        assert a == b

    def test_dimensions_and_normalized(self):
        vecs = embeddings.local_embed(["alpha beta", "gamma"], dim=64)
        assert [len(v) for v in vecs] == [64, 64]
        # L2 norm ~= 1.0 (nonzero vectors are normalized).
        n = sum(x * x for x in vecs[0]) ** 0.5
        assert abs(n - 1.0) < 1e-3

    def test_different_inputs_differ(self):
        a = embeddings.local_embed(["machine learning"])
        b = embeddings.local_embed(["cooking recipes"])
        assert a != b

    def test_empty_text_still_returns_vector(self):
        vecs = embeddings.local_embed([""], dim=8)
        assert len(vecs) == 1 and len(vecs[0]) == 8

    def test_default_dim_matches_settings(self):
        vecs = embeddings.local_embed(["x"])
        assert len(vecs[0]) == settings.EMBEDDINGS_DIM


class TestHash:
    def test_stable(self):
        assert embeddings.embedding_hash("a b") == embeddings.embedding_hash("a b")

    def test_differs_by_content(self):
        assert embeddings.embedding_hash("a") != embeddings.embedding_hash("b")


class TestProviderShortCircuit:
    def test_embed_texts_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        assert embeddings.embed_texts(["x"]) is None
        assert embeddings.get_embedding("x") is None
        assert embeddings.embed_available() is False

    def test_embed_texts_requires_list(self):
        with pytest.raises(TypeError):
            embeddings.embed_texts("not a list")  # type: ignore[arg-type]

    def test_embed_texts_empty_list(self):
        # Empty batch is a no-op even with provider available.
        assert embeddings.embed_texts([]) == []

    def test_embed_available_when_enabled(self):
        assert embeddings.embed_available() == bool(
            settings.AI_ENABLED and settings.AI_BASE_URL and settings.EMBEDDINGS_MODEL
        )


class TestBudget:
    def test_budget_empty_is_zero(self, db_session, kb_user):
        b = embeddings.embedding_budget(db_session, kb_user.id)
        assert b["today"] == 0
        assert b["limit"] == settings.EMBEDDINGS_DAILY_LIMIT
        assert b["remaining"] == settings.EMBEDDINGS_DAILY_LIMIT
        assert embeddings.budget_allows(db_session, kb_user.id)

    def test_budget_counts_provider_rows(self, db_session, kb_user):
        doc = KbDocument(user_id=kb_user.id, title="d", doc_type="md", status="new")
        db_session.add(doc)
        db_session.flush()
        db_session.add_all([
            KbEmbedding(user_id=kb_user.id, chunk_id=1, model="text-embedding-3-small",
                        dim=8, vector="[0.0]*8"),
            KbEmbedding(user_id=kb_user.id, chunk_id=2, model=embeddings.LOCAL_MODEL,
                        dim=8, vector="[0.0]*8"),
        ])
        db_session.commit()
        b = embeddings.embedding_budget(db_session, kb_user.id)
        # Local rows are budget-exempt.
        assert b["today"] == 1
        assert b["remaining"] == settings.EMBEDDINGS_DAILY_LIMIT - 1
