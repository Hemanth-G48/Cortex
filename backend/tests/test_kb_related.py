"""Related-document inference tests (Phase 2, Idea 17, phrase 68).

Covers document-pair similarity (above/below ``KB_SIM_THRESHOLD``),
shared-concept edges, backlink symmetry, incremental scoping, and the
``GET /api/kb/documents/{id}/related`` endpoint — all per-user scoped.
"""
from __future__ import annotations

from app.config import settings
from app.models import KbChunk, KbConcept, KbDocument, KbEdge, KbEmbedding, User
from app.services import embeddings
from app.services.kb import KbService
from app.services.kb import graph
from app.services.kb.related import (
    doc_avg_embedding,
    infer_related_for_doc,
    infer_shared_concepts,
    related_documents,
)
from app.services.embeddings import local_embed

AUTH = "Authorization"


def _signup(client, uname="rel-user", email="rel@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Rel",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db, user_id: int, title: str, text: str) -> int:
    """Create a document + one chunk directly in the DB."""
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        status="unchanged",
        extracted_text=text,
    )
    db.add(doc)
    db.flush()
    db.add(
        KbChunk(
            user_id=user_id,
            document_id=doc.id,
            seq=0,
            content=text,
            char_start=0,
            char_end=len(text),
        )
    )
    db.commit()
    return doc.id


def _embed_doc(db, user_id: int, doc_id: int) -> None:
    """Write KbEmbedding rows for the doc's chunks using the local embedder."""
    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc_id, KbChunk.user_id == user_id)
        .order_by(KbChunk.seq)
        .all()
    )
    if not chunks:
        return
    vectors = local_embed([c.content for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        db.add(
            KbEmbedding(
                user_id=user_id,
                chunk_id=chunk.id,
                model="local",
                dim=len(vec),
                content_hash=embeddings.embedding_hash(chunk.content),
                vector=KbService.json_dumps(vec),
            )
        )
    db.commit()


class TestDocAvgEmbedding:
    def test_returns_mean_vector(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "alpha beta gamma")
        _embed_doc(db_session, user.id, doc_id)

        vec = doc_avg_embedding(db_session, user.id, doc_id)
        assert vec is not None
        assert len(vec) == settings.EMBEDDINGS_DIM

    def test_no_embeddings_returns_none(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "alpha beta gamma")
        assert doc_avg_embedding(db_session, user.id, doc_id) is None

    def test_per_user_isolation(self, client, db_session):
        _signup(client, "rel-a", "rel-a@test.com")
        _signup(client, "rel-b", "rel-b@test.com")
        user_a = db_session.query(User).filter(User.username == "rel-a").first()
        user_b = db_session.query(User).filter(User.username == "rel-b").first()

        doc_a = _make_doc(db_session, user_a.id, "A", "shared text here")
        _embed_doc(db_session, user_a.id, doc_a)

        # User B has no embeddings for user A's doc.
        assert doc_avg_embedding(db_session, user_b.id, doc_a) is None


class TestInferRelatedForDoc:
    def test_above_threshold_creates_related_edge(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        # Identical text → cosine ≈ 1.0 (above the 0.75 threshold).
        doc_a = _make_doc(db_session, user.id, "A", "the quick brown fox jumps")
        doc_b = _make_doc(db_session, user.id, "B", "the quick brown fox jumps")
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)

        written = infer_related_for_doc(db_session, user.id, doc_a)
        assert written >= 1

        edges = (
            db_session.query(KbEdge)
            .filter(
                KbEdge.user_id == user.id,
                KbEdge.source_document_id == doc_a,
                KbEdge.relation == "RELATED",
            )
            .all()
        )
        assert len(edges) >= 1
        assert edges[0].target_document_id == doc_b
        assert edges[0].provenance == "auto"
        assert edges[0].weight >= settings.KB_SIM_THRESHOLD

    def test_below_threshold_no_edge(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a = _make_doc(db_session, user.id, "A", "alpha beta gamma delta epsilon")
        doc_b = _make_doc(
            db_session, user.id, "B", "completely unrelated xyz qwerty 123456"
        )
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)

        written = infer_related_for_doc(db_session, user.id, doc_a)
        assert written == 0

    def test_overwrite_policy_replaces_stale_edge(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a = _make_doc(db_session, user.id, "A", "same sentence content here")
        doc_b = _make_doc(db_session, user.id, "B", "same sentence content here")
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)

        infer_related_for_doc(db_session, user.id, doc_a)
        count1 = (
            db_session.query(KbEdge)
            .filter(
                KbEdge.user_id == user.id,
                KbEdge.source_document_id == doc_a,
                KbEdge.relation == "RELATED",
            )
            .count()
        )
        # Re-running must not create a duplicate row.
        infer_related_for_doc(db_session, user.id, doc_a)
        count2 = (
            db_session.query(KbEdge)
            .filter(
                KbEdge.user_id == user.id,
                KbEdge.source_document_id == doc_a,
                KbEdge.relation == "RELATED",
            )
            .count()
        )
        assert count1 == count2 == 1

    def test_missing_document_returns_zero(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()
        assert infer_related_for_doc(db_session, user.id, 99999) == 0


class TestInferSharedConcepts:
    def test_shared_concept_creates_shares_concept_edge(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        concept = KbConcept(user_id=user.id, canonical_name="Gravity")
        db_session.add(concept)
        db_session.flush()

        doc_a = _make_doc(db_session, user.id, "A", "Gravity is real.")
        doc_b = _make_doc(db_session, user.id, "B", "Gravity pulls things.")
        db_session.commit()

        # MENTIONS edges to the shared concept (provenance rule).
        graph.add_edge(
            db_session, user.id, doc_a, target_concept_id=concept.id,
            relation="MENTIONS", weight=1.0, provenance="rule",
            target_type="concept", overwrite=True,
        )
        graph.add_edge(
            db_session, user.id, doc_b, target_concept_id=concept.id,
            relation="MENTIONS", weight=1.0, provenance="rule",
            target_type="concept", overwrite=True,
        )
        db_session.commit()

        written = infer_shared_concepts(db_session, user.id)
        assert written >= 1

        edges = (
            db_session.query(KbEdge)
            .filter(
                KbEdge.user_id == user.id,
                KbEdge.relation == "SHARES_CONCEPT",
            )
            .all()
        )
        assert len(edges) >= 1

    def test_no_shared_concepts_no_edges(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        _make_doc(db_session, user.id, "A", "Hello")
        _make_doc(db_session, user.id, "B", "World")
        db_session.commit()

        assert infer_shared_concepts(db_session, user.id) == 0


class TestRelatedDocuments:
    def test_returns_related_docs_with_relations(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a = _make_doc(db_session, user.id, "A", "the quick brown fox jumps")
        doc_b = _make_doc(db_session, user.id, "B", "the quick brown fox jumps")
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)

        result = related_documents(db_session, user.id, doc_a)
        assert result["document_id"] == doc_a
        assert len(result["related"]) >= 1
        assert result["related"][0]["id"] == doc_b
        assert result["related"][0]["relation"] == "RELATED"
        assert result["related"][0]["weight"] >= settings.KB_SIM_THRESHOLD

    def test_backlink_symmetry_from_wikilink(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a_id = _make_doc(
            db_session, user.id, "A", "See [[Notes/World]] for details."
        )
        doc_b_id = _make_doc(db_session, user.id, "B", "Back to A.")
        # Give B a path that [[Notes/World]] resolves to.
        db_session.query(KbDocument).filter(KbDocument.id == doc_b_id).update(
            {"path_rel": "notes/world.md", "title": "World"}
        )
        db_session.commit()

        doc_a = db_session.query(KbDocument).get(doc_a_id)
        graph.build_wikilink_edges(db_session, user.id, doc_a, backlinks=True)
        db_session.commit()

        # A has an outbound WIKILINK to B; B has an inbound BACKLINK from A.
        result_b = related_documents(
            db_session, user.id, doc_b_id, infer=False
        )
        relations = {r["relation"] for r in result_b["related"]}
        assert "BACKLINK" in relations

    def test_relation_filter(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a = _make_doc(db_session, user.id, "A", "the quick brown fox jumps")
        doc_b = _make_doc(db_session, user.id, "B", "the quick brown fox jumps")
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)
        # Add a WIKILINK too so there are two relation types.
        db_session.query(KbDocument).filter(KbDocument.id == doc_b).update(
            {"path_rel": "b.md"}
        )
        db_session.commit()
        graph.add_edge(
            db_session, user.id, doc_a, target_document_id=doc_b,
            relation="WIKILINK", weight=1.0, provenance="rule",
            overwrite=True,
        )
        db_session.commit()

        only_wikilinks = related_documents(
            db_session, user.id, doc_a, relation="WIKILINK", infer=False
        )
        assert all(r["relation"] == "WIKILINK" for r in only_wikilinks["related"])

        only_related = related_documents(
            db_session, user.id, doc_a, relation="RELATED", infer=False
        )
        assert all(r["relation"] == "RELATED" for r in only_related["related"])


class TestRelatedApi:
    def test_get_related_endpoint(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "rel-user").first()

        doc_a = _make_doc(db_session, user.id, "A", "the quick brown fox jumps")
        doc_b = _make_doc(db_session, user.id, "B", "the quick brown fox jumps")
        _embed_doc(db_session, user.id, doc_a)
        _embed_doc(db_session, user.id, doc_b)

        resp = client.get(
            f"/api/kb/documents/{doc_a}/related",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] == doc_a
        assert "related" in data
        assert data["method"] == "embedding"
        assert len(data["related"]) >= 1

    def test_get_related_404_for_other_users_doc(self, client, db_session):
        token_a = _signup(client, "rel-x", "rel-x@test.com")
        token_b = _signup(client, "rel-y", "rel-y@test.com")
        user_a = db_session.query(User).filter(User.username == "rel-x").first()

        doc_a = _make_doc(db_session, user_a.id, "A", "content here")
        resp = client.get(
            f"/api/kb/documents/{doc_a}/related",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    def test_related_404_for_missing_doc(self, client):
        token = _signup(client)
        resp = client.get(
            "/api/kb/documents/99999/related",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 404
