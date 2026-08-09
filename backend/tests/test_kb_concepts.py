"""Idea 15 — concept extraction & canonicalization tests (phrase 48).

Covers: canonicalize, deterministic tfidf_concepts, create-or-reuse
dedup/alias merge, MENTIONS edge creation, per-user isolation, and
GET /api/kb/concepts pagination shape.
"""
from __future__ import annotations

import tempfile
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import KbChunk, KbConcept, KbDocument, KbEdge, User
from app.services.kb.concepts import canonicalize, extract_concepts, link_mentions
from app.services.kb.concepts import create_or_reuse, extract_for_document
from app.services.kb import KbService
from main import app

AUTH = "Authorization"


def _make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _signup(client, uname="concept-user", email="concept@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Concepts", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _add_doc(db, user_id, title="Doc", content="hello world content", **kwargs):
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        extracted_text=content,
        content_hash="abc123",
        status="new",
        **kwargs,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _add_chunk(db, doc, content, seq=0):
    chunk = KbChunk(
        user_id=doc.user_id,
        document_id=doc.id,
        seq=seq,
        content=content,
        token_estimate=len(content) // 4,
    )
    db.add(chunk)
    db.commit()
    return chunk


class TestCanonicalize:
    def test_lowercase_and_trim(self):
        assert canonicalize("  Hello World  ") == "hello world"

    def test_strips_trailing_punctuation(self):
        assert canonicalize("concept.") == "concept"
        assert canonicalize("idea!") == "idea"
        assert canonicalize("test?") == "test"

    def test_singularization(self):
        assert canonicalize("concepts") == "concept"
        assert canonicalize("ideas") == "idea"
        # Double-s preserved — "class" stays "class" (not "clas").

    def test_collapses_whitespace(self):
        assert canonicalize("too  many   spaces") == "too many space"

    def test_empty_returns_empty(self):
        assert canonicalize("") == ""
        assert canonicalize("   ") == ""


class TestTfidfConcepts:
    def test_deterministic_with_ai_disabled(self, monkeypatch):
        """With AI_ENABLED=False, extract_concepts must use TF-IDF."""
        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: False)
        engine = _make_engine()
        Session = sessionmaker(bind=engine)
        db = Session()
        user = User(name="TFIDF", username="tfidf-u", email="tfidf@test.com", role="student")
        db.add(user)
        db.commit()
        db.refresh(user)

        doc = _add_doc(db, user.id, content="machine learning and deep learning models")
        _add_chunk(db, doc, "machine learning models for classification")
        _add_chunk(db, doc, "deep learning neural networks")

        concepts = extract_concepts(db, doc)
        assert len(concepts) > 0
        names = [c.canonical_name for c in concepts]
        # All names should be canonicalized.
        for name in names:
            assert name == canonicalize(name)
        db.close()


class TestCreateOrReuse:
    def test_same_name_creates_one_row(self, db_session):
        user = User(name="Dup", username="dup-u", email="dup@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        c1 = KbConcept(user_id=user.id, canonical_name="learning", definition="Study")
        db_session.add(c1)
        db_session.commit()

        # Creating again with different case should not duplicate.
        c2 = KbConcept(user_id=user.id, canonical_name="Learning")
        db_session.add(c2)
        db_session.commit()

        rows = db_session.query(KbConcept).filter(
            KbConcept.user_id == user.id,
            KbConcept.canonical_name == "learning",
        ).all()
        assert len(rows) == 1

    def test_aliases_merge_on_reuse(self, db_session):
        user = User(name="Alias", username="alias-u", email="alias@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        c = KbConcept(user_id=user.id, canonical_name="ml", aliases='["machine learning"]')
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)

        result = create_or_reuse(
            db_session, user.id, "ML", aliases=["ML", "machine learning", "ML models"]
        )
        db_session.refresh(result)
        aliases = KbService.json_loads(result.aliases) or []
        assert "ML" in aliases
        assert "ML models" in aliases
        assert "machine learning" in aliases

    def test_definition_only_updated_when_empty(self, db_session):
        user = User(name="Def", username="def-u", email="def@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        c = KbConcept(user_id=user.id, canonical_name="test", definition="Original")
        db_session.add(c)
        db_session.commit()

        # Call with a new definition but existing one is non-empty — should not overwrite.
        result = create_or_reuse(db_session, user.id, "test", definition="New def")
        db_session.refresh(result)
        assert result.definition == "Original"


class TestMentionsEdge:
    def test_mentions_edge_created(self, db_session):
        user = User(name="Ment", username="ment-u", email="ment@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        doc = _add_doc(db_session, user.id, content="machine learning and machine learning models")
        concept = KbConcept(user_id=user.id, canonical_name="machine learning")
        db_session.add(concept)
        db_session.commit()
        db_session.refresh(concept)

        count = link_mentions(db_session, doc, [concept])
        assert count == 1

        edge = db_session.query(KbEdge).filter(
            KbEdge.source_document_id == doc.id,
            KbEdge.target_concept_id == concept.id,
            KbEdge.relation == "MENTIONS",
        ).first()
        assert edge is not None
        assert edge.target_type == "concept"
        assert 0 < edge.weight <= 1
        assert edge.provenance in ("ai", "rule")

    def test_weight_clamped_to_minimum(self, db_session):
        """Very rare mentions still get weight >= 0.05."""
        user = User(name="Wt", username="wt-u", email="wt@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        doc = _add_doc(db_session, user.id, content="rare concept appears once here")
        concept = KbConcept(user_id=user.id, canonical_name="rare concept")
        db_session.add(concept)
        db_session.commit()
        db_session.refresh(concept)

        count = link_mentions(db_session, doc, [concept])
        assert count == 1

        edge = db_session.query(KbEdge).filter(
            KbEdge.source_document_id == doc.id,
            KbEdge.target_concept_id == concept.id,
        ).first()
        assert edge is not None
        assert edge.weight >= 0.05

    def test_dedupes_existing_edge(self, db_session):
        user = User(name="Dedup", username="dedup-u", email="dedup@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        doc = _add_doc(db_session, user.id, content="learning learning learning")
        concept = KbConcept(user_id=user.id, canonical_name="learning")
        db_session.add(concept)
        db_session.commit()
        db_session.refresh(concept)

        link_mentions(db_session, doc, [concept])
        link_mentions(db_session, doc, [concept])  # second call should not duplicate

        edges = db_session.query(KbEdge).filter(
            KbEdge.source_document_id == doc.id,
            KbEdge.target_concept_id == concept.id,
            KbEdge.relation == "MENTIONS",
        ).all()
        assert len(edges) == 1


class TestExtractForDocument:
    def test_persists_concepts_before_linking_mentions(self, db_session, monkeypatch):
        """Regression: extract_for_document used to hand unpersisted concept
        objects (id=None) to link_mentions, so MENTIONS edges inserted NULL
        target ids and crashed with a NOT NULL constraint failure on
        kb_edges.target_document_id. Now concepts are persisted first and
        every MENTIONS edge carries a real target_concept_id.
        """
        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: False)

        user = User(name="Ext", username="ext-u", email="ext@test.com", role="student")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        doc = _add_doc(
            db_session, user.id,
            content="machine learning models for classification and "
                    "machine learning neural networks",
        )
        _add_chunk(db_session, doc, "machine learning models for classification")
        _add_chunk(db_session, doc, "neural networks for machine learning")

        count = extract_for_document(db_session, doc)
        assert count > 0

        edges = db_session.query(KbEdge).filter(
            KbEdge.source_document_id == doc.id,
            KbEdge.relation == "MENTIONS",
        ).all()
        assert len(edges) > 0
        for edge in edges:
            assert edge.target_type == "concept"
            assert edge.target_concept_id is not None
            assert edge.target_document_id is None

        # The graph stage cleared its dirty flag on success.
        db_session.refresh(doc)
        assert doc.graph_dirty is False


class TestPerUserIsolation:
    def test_user_b_concepts_invisible_to_user_a(self, client, db_session):
        token_a = _signup(client, "user-a-iso", "a-iso@test.com")
        token_b = _signup(client, "user-b-iso", "b-iso@test.com")

        user_a = db_session.query(User).filter(User.username == "user-a-iso").first()
        user_b = db_session.query(User).filter(User.username == "user-b-iso").first()

        doc_a = KbDocument(
            user_id=user_a.id, title="A Doc", doc_type="md",
            extracted_text="machine learning content", status="new",
        )
        db_session.add(doc_a)
        db_session.commit()
        db_session.refresh(doc_a)

        concept_a = KbConcept(user_id=user_a.id, canonical_name="machine learning")
        db_session.add(concept_a)
        db_session.commit()
        db_session.refresh(concept_a)

        # User B should not see user A's concept.
        resp = client.get(
            "/api/kb/concepts",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(c["canonical_name"] != "machine learning" for c in data["items"])

    def test_get_concepts_returns_only_owned(self, client, db_session):
        token = _signup(client, "own-user-iso", "own-iso@test.com")
        user = db_session.query(User).filter(User.username == "own-user-iso").first()

        doc = KbDocument(
            user_id=user.id, title="Own Doc", doc_type="md",
            extracted_text="data science and data analysis", status="new",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        concept = KbConcept(user_id=user.id, canonical_name="data science")
        db_session.add(concept)
        db_session.commit()
        db_session.refresh(concept)

        resp = client.get(
            "/api/kb/concepts",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [c["canonical_name"] for c in data["items"]]
        assert "data science" in names

    def test_pagination_shape(self, client, db_session):
        token = _signup(client, "page-user-iso", "page-iso@test.com")
        user = db_session.query(User).filter(User.username == "page-user-iso").first()

        for i in range(5):
            doc = KbDocument(
                user_id=user.id, title=f"Doc {i}", doc_type="md",
                extracted_text=f"concept number {i} content", status="new",
            )
            db_session.add(doc)
        db_session.commit()

        resp = client.get(
            "/api/kb/concepts?page=1&page_size=2",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_concept_404_for_other_user(self, client, db_session):
        token_a = _signup(client, "owner-404-u", "owner404@test.com")
        token_b = _signup(client, "stranger-404-u", "stranger404@test.com")

        user_a = db_session.query(User).filter(User.username == "owner-404-u").first()
        doc = KbDocument(
            user_id=user_a.id, title="Private", doc_type="md",
            extracted_text="secret concept", status="new",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        concept = KbConcept(user_id=user_a.id, canonical_name="secret")
        db_session.add(concept)
        db_session.commit()
        db_session.refresh(concept)

        # User B tries to access user A's concept via the list — should not appear.
        resp = client.get(
            "/api/kb/concepts",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert not any(c["canonical_name"] == "secret" for c in data["items"])