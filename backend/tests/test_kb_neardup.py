"""Near-duplicate detection tests (Phase 2, Idea 19, phrase 87).

Tests candidate generation, scanning, listing, merging, archiving,
and per-user isolation using hermetic local embeddings.
"""
from __future__ import annotations

import os

from app.models import KbChunk, KbDocument, KbEdge, KbEmbedding, User
from app.services.embeddings import local_embed
from app.services.kb import KbService
from app.services.kb.neardup import (
    archive_document,
    candidate_pairs,
    list_duplicates,
    merge_documents,
    scan_duplicates,
)

AUTH = "Authorization"


def _signup(client, uname="dup-user", email="dup@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Dup",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload_doc(db_session, user_id: int, filename: str, content: bytes) -> int:
    """Create a document + chunk directly in the DB.

    The upload endpoint content-dedups identical uploads, which would
    prevent near-dup tests from ever creating two identical documents.
    Creating rows directly lets identical content coexist.
    """
    text = content.decode("utf-8")
    doc = KbDocument(
        user_id=user_id,
        title=os.path.splitext(filename)[0],
        doc_type="md",
        status="new",
        content_hash=KbService.content_hash(content),
        extracted_text=text,
    )
    db_session.add(doc)
    db_session.flush()
    db_session.add(
        KbChunk(
            user_id=user_id,
            document_id=doc.id,
            seq=0,
            content=text,
            char_start=0,
            char_end=len(text),
        )
    )
    db_session.commit()
    return doc.id


def _add_embeddings(db_session, user_id: int, doc_id: int):
    """Create KbEmbedding rows for every chunk of *doc_id* using local_embed."""
    chunks = (
        db_session.query(KbChunk)
        .filter(KbChunk.document_id == doc_id, KbChunk.user_id == user_id)
        .order_by(KbChunk.seq)
        .all()
    )
    if not chunks:
        return
    vectors = local_embed([c.content for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        emb = KbEmbedding(
            user_id=user_id,
            chunk_id=chunk.id,
            model="local",
            dim=len(vec),
            content_hash=None,
            vector=KbService.json_dumps(vec),
        )
        db_session.add(emb)
    db_session.commit()


class TestScanDuplicates:
    def test_identical_chunks_flagged(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"hello world")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"Hello World.")

        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)

        pairs = scan_duplicates(db_session, user.id)
        assert len(pairs) >= 1
        assert pairs[0]["similarity"] == 1.0
        assert pairs[0]["method"] == "embedding"

    def test_close_paraphrase_flagged(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        # Long text sharing all tokens but one — with the token-scatter embedder,
        # similarity ~= shared/(shared+1), so ~22 shared tokens clears the 0.95
        # threshold while a single word differs (a real paraphrase, not identical).
        doc_a = _upload_doc(
            db_session,
            user.id,
            "a.md",
            b"the quick brown fox jumps over the lazy dog and runs through the "
            b"forest every morning before sunrise to catch the early worm",
        )
        doc_b = _upload_doc(
            db_session,
            user.id,
            "b.md",
            b"the quick brown fox leaps over the lazy dog and runs through the "
            b"forest every morning before sunrise to catch the early worm",
        )

        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)

        pairs = scan_duplicates(db_session, user.id)
        assert len(pairs) >= 1
        assert pairs[0]["similarity"] >= 0.95

    def test_different_texts_not_flagged(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"alpha beta gamma delta epsilon")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"completely unrelated xyz 123")

        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)

        pairs = scan_duplicates(db_session, user.id)
        assert len(pairs) == 0

    def test_candidate_pairs_skips_same_document(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_id = _upload_doc(db_session, user.id, "a.md", b"hello world hello world")
        _add_embeddings(db_session, user.id, doc_id)

        # Only one document, so no cross-document pairs should exist.
        pairs = candidate_pairs(db_session, user.id)
        for emb_a, emb_b, sim in pairs:
            assert emb_a.chunk.document_id != emb_b.chunk.document_id

    def test_list_duplicates(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"identical content")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"Identical content.")

        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)
        scan_duplicates(db_session, user.id)

        items = list_duplicates(db_session, user.id)
        assert len(items) >= 1
        assert items[0]["similarity"] == 1.0
        assert items[0]["method"] == "embedding"
        assert items[0]["document_id"] != items[0]["duplicate_of_id"]

    def test_merge_documents_reassigns_chunks(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"keep this content")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"merge this content")

        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)
        scan_duplicates(db_session, user.id)

        result = merge_documents(db_session, user.id, keep_id=doc_a, merge_ids=[doc_b])
        assert result["kept"] == doc_a
        assert result["merged"] == 1

        # Chunks from doc_b should now point to doc_a.
        chunks = (
            db_session.query(KbChunk)
            .filter(KbChunk.document_id == doc_a, KbChunk.user_id == user.id)
            .all()
        )
        assert len(chunks) >= 2

        # doc_b should be gone.
        gone = db_session.query(KbDocument).filter(KbDocument.id == doc_b).first()
        assert gone is None

    def test_archive_document_sets_status(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_id = _upload_doc(db_session, user.id, "a.md", b"some content")
        result = archive_document(db_session, user.id, doc_id)
        assert result["ok"] is True

        doc = db_session.query(KbDocument).filter(KbDocument.id == doc_id).first()
        assert doc.status == "archived"

    def test_per_user_isolation(self, client, db_session):
        token_a = _signup(client, uname="user-a", email="a@test.com")
        token_b = _signup(client, uname="user-b", email="b@test.com")

        user_a = db_session.query(User).filter(User.username == "user-a").first()
        user_b = db_session.query(User).filter(User.username == "user-b").first()

        doc_a1 = _upload_doc(db_session, user_a.id, "a1.md", b"shared content")
        doc_a2 = _upload_doc(db_session, user_a.id, "a2.md", b"Shared content!")
        doc_b1 = _upload_doc(db_session, user_b.id, "b1.md", b"different content")

        _add_embeddings(db_session, user_a.id, doc_a1)
        _add_embeddings(db_session, user_a.id, doc_a2)
        _add_embeddings(db_session, user_b.id, doc_b1)

        # User A has a duplicate pair.
        pairs_a = scan_duplicates(db_session, user_a.id)
        assert len(pairs_a) >= 1

        # User B has no duplicates.
        pairs_b = scan_duplicates(db_session, user_b.id)
        assert len(pairs_b) == 0

        # User B's list_duplicates is empty.
        items_b = list_duplicates(db_session, user_b.id)
        assert len(items_b) == 0

    def test_get_duplicates_endpoint(self, client):
        token = _signup(client)
        resp = client.get(
            "/api/kb/duplicates",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "method" in data

    def test_scan_endpoint(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"duplicate text")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"Duplicate text.")
        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)

        resp = client.post(
            "/api/kb/duplicates/scan",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_merge_endpoint(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_a = _upload_doc(db_session, user.id, "a.md", b"keep content")
        doc_b = _upload_doc(db_session, user.id, "b.md", b"merge content")
        _add_embeddings(db_session, user.id, doc_a)
        _add_embeddings(db_session, user.id, doc_b)
        scan_duplicates(db_session, user.id)

        resp = client.post(
            "/api/kb/duplicates/merge",
            json={"keep_id": doc_a, "merge_ids": [doc_b]},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["merged"] == 1

    def test_archive_endpoint(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "dup-user").first()

        doc_id = _upload_doc(db_session, user.id, "a.md", b"content")

        resp = client.post(
            f"/api/kb/duplicates/{doc_id}/archive",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_archive_nonexistent_doc_returns_404(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/kb/duplicates/99999/archive",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_candidate_pairs_returns_empty_for_new_user(self, client, db_session):
        token = _signup(client, uname="empty-user", email="empty@test.com")
        user = db_session.query(User).filter(User.username == "empty-user").first()
        pairs = candidate_pairs(db_session, user.id)
        assert pairs == []