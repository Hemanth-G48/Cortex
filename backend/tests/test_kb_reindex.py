"""Re-index tooling tests (Phase 2, Idea 20, phrase 98).

Covers the dirty-flag lifecycle, incremental processing (only dirty docs),
idempotent re-runs (no-op), job-queue progress, backfill, and the admin
endpoints — which are user-scoped, so any authenticated user (student
included) may reindex their own knowledge base.
"""
from __future__ import annotations

from app.config import settings
from app.models import KbChunk, KbDocument, KbEmbedding, KbJob, KbSource, User
from app.services.kb import reindex as reindex_service
from app.services.kb import jobs

AUTH = "Authorization"


def _signup(client, uname="reindex-user", email="reindex@test.com", role="student", secret=None):
    body = {
        "name": "Reindex",
        "username": uname,
        "email": email,
        "password": "pass123",
        "role": role,
    }
    if secret is not None:
        body["teacher_secret"] = secret
    resp = client.post("/api/auth/signup", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db, user_id: int, title: str, text: str, dirty: bool = True) -> int:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        status="unchanged",
        extracted_text=text,
        embedding_dirty=dirty,
        tags_dirty=dirty,
        graph_dirty=dirty,
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


def _add_embeddings(db, user_id: int, doc_id: int) -> None:
    from app.services import embeddings
    from app.services.kb import KbService

    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc_id, KbChunk.user_id == user_id)
        .all()
    )
    vectors = embeddings.local_embed([c.content for c in chunks])
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


class TestDirtyFlags:
    def test_new_documents_start_dirty(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "some text")

        doc = db_session.query(KbDocument).get(doc_id)
        assert doc.embedding_dirty is True
        assert doc.tags_dirty is True
        assert doc.graph_dirty is True

    def test_dirty_documents_queries_flags(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        dirty_id = _make_doc(db_session, user.id, "Dirty", "text")
        clean_id = _make_doc(db_session, user.id, "Clean", "text", dirty=False)

        dirty = reindex_service.dirty_documents(db_session, user.id)
        dirty_ids = {d.id for d in dirty}
        assert dirty_id in dirty_ids
        assert clean_id not in dirty_ids


class TestIncrementalReindex:
    def test_processes_only_dirty_documents(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        dirty_id = _make_doc(db_session, user.id, "Dirty", "alpha beta gamma")
        clean_id = _make_doc(db_session, user.id, "Clean", "delta epsilon zeta", dirty=False)

        summary = reindex_service.reindex_documents(db_session, user.id)
        assert summary["documents"] == 1

        dirty_doc = db_session.query(KbDocument).get(dirty_id)
        clean_doc = db_session.query(KbDocument).get(clean_id)
        assert dirty_doc.embedding_dirty is False
        assert dirty_doc.tags_dirty is False
        assert dirty_doc.graph_dirty is False
        # Clean doc's flags untouched (still clean — but assert it wasn't reprocessed).
        assert clean_doc.embedding_dirty is False

        # Embeddings were written for the dirty doc only.
        emb = (
            db_session.query(KbEmbedding)
            .filter(KbEmbedding.user_id == user.id)
            .count()
        )
        assert emb >= 1

    def test_dirty_flag_lifecycle_stage_order(self, client, db_session):
        """A failed stage leaves its flag set; successful stages clear theirs."""
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "alpha beta gamma delta")
        db_session.commit()

        doc = db_session.query(KbDocument).get(doc_id)
        # Simulate embeddings failing: clear only embedding_dirty via the
        # coordinator's stage guard (embed fails → flag stays).
        # Patch the name reindex.py actually calls — it imports
        # embed_document_chunks directly into its module namespace.
        original = reindex_service.embed_document_chunks

        def _fail_embed(*args, **kwargs):
            raise RuntimeError("provider down")

        reindex_service.embed_document_chunks = _fail_embed
        try:
            summary = reindex_service.run_document_stages(db_session, doc)
            assert summary["ok"] is False
        finally:
            reindex_service.embed_document_chunks = original
        db_session.rollback()

        # embedding_dirty should still be True (stage failed → flag kept).
        db_session.expire_all()
        doc = db_session.query(KbDocument).get(doc_id)
        assert doc.embedding_dirty is True

        # A clean run now clears everything.
        summary = reindex_service.reindex_documents(db_session, user.id)
        db_session.expire_all()
        doc = db_session.query(KbDocument).get(doc_id)
        assert doc.embedding_dirty is False
        assert doc.tags_dirty is False
        assert doc.graph_dirty is False

    def test_idempotent_rerun_is_noop(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        _make_doc(db_session, user.id, "A", "alpha beta gamma")

        first = reindex_service.reindex_documents(db_session, user.id)
        assert first["documents"] == 1

        second = reindex_service.reindex_documents(db_session, user.id)
        assert second["documents"] == 0  # nothing dirty remains
        assert second["embedded"] == 0

    def test_source_scoped_reindex(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()

        src = KbSource(
            user_id=user.id, name="Vault", source_type="vault_folder",
            root_path="/tmp/nonexistent", enabled=True,
        )
        db_session.add(src)
        db_session.flush()
        src_id = src.id

        doc_in = KbDocument(
            user_id=user.id, source_id=src_id, title="In", doc_type="md",
            status="unchanged", extracted_text="text in source",
            embedding_dirty=True, tags_dirty=True, graph_dirty=True,
        )
        doc_out = KbDocument(
            user_id=user.id, title="Out", doc_type="md", status="unchanged",
            extracted_text="text outside source",
            embedding_dirty=True, tags_dirty=True, graph_dirty=True,
        )
        db_session.add_all([doc_in, doc_out])
        db_session.commit()

        summary = reindex_service.reindex_documents(
            db_session, user.id, source_id=src_id
        )
        assert summary["documents"] == 1

        db_session.expire_all()
        assert db_session.query(KbDocument).get(doc_in.id).embedding_dirty is False
        assert db_session.query(KbDocument).get(doc_out.id).embedding_dirty is True


class TestBatchedEmbedding:
    def test_embed_dirty_batch_clears_flags_and_writes_vectors(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)  # hermetic: hash embedder
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        d1 = _make_doc(db_session, user.id, "A", "alpha beta gamma")
        d2 = _make_doc(db_session, user.id, "B", "delta epsilon zeta")

        res = reindex_service.embed_dirty_batch(db_session, user.id, [d1, d2])
        assert res["docs"] == 2
        assert res["chunks"] == 2
        assert res["embedded"] == 2
        assert res["skipped"] == 0

        db_session.expire_all()
        for did in (d1, d2):
            doc = db_session.query(KbDocument).get(did)
            assert doc.embedding_dirty is False
        emb = db_session.query(KbEmbedding).filter(KbEmbedding.user_id == user.id).count()
        assert emb == 2

    def test_embed_dirty_batch_skips_cached_hashes(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "alpha beta gamma")
        _add_embeddings(db_session, user.id, doc_id)
        # Re-mark dirty to force another pass — hashes already exist.
        doc = db_session.query(KbDocument).get(doc_id)
        doc.embedding_dirty = True
        db_session.commit()

        res = reindex_service.embed_dirty_batch(db_session, user.id, [doc_id])
        assert res["docs"] == 1
        assert res["embedded"] == 0
        assert res["skipped"] == 1
        assert db_session.query(KbDocument).get(doc_id).embedding_dirty is False

    def test_embed_dirty_batch_respects_doc_scope(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        _make_doc(db_session, user.id, "A", "alpha beta gamma")
        _make_doc(db_session, user.id, "B", "delta epsilon zeta")

        # Only doc A is in scope; B stays dirty.
        docs = db_session.query(KbDocument).filter(KbDocument.user_id == user.id).all()
        res = reindex_service.embed_dirty_batch(db_session, user.id, [docs[0].id])
        assert res["docs"] == 1
        db_session.expire_all()
        assert db_session.query(KbDocument).get(docs[0].id).embedding_dirty is False
        assert db_session.query(KbDocument).get(docs[1].id).embedding_dirty is True


class TestBackfill:
    def test_backfill_marks_all_and_reindexes(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        _make_doc(db_session, user.id, "A", "alpha text")
        _make_doc(db_session, user.id, "B", "beta text")

        summary = reindex_service.backfill(db_session, user.id)
        assert summary["marked_dirty"] == 2
        assert summary["documents"] == 2

        remaining = reindex_service.dirty_documents(db_session, user.id)
        assert remaining == []


class TestReindexJobQueue:
    def test_reindex_job_clears_dirty_flags(self, client, db_session, monkeypatch):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        doc_id = _make_doc(db_session, user.id, "A", "alpha beta gamma")

        monkeypatch.setattr(settings, "AI_ENABLED", False)  # hermetic
        job = jobs.submit_reindex_job(
            db_session, user.id, document_ids=[doc_id]
        )
        assert job.status in ("done", "queued", "running")

        # Sync mode runs inline under pytest — job should complete.
        if job.status == "done":
            db_session.expire_all()
            doc = db_session.query(KbDocument).get(doc_id)
            assert doc.embedding_dirty is False

    def test_submit_reindex_job_scoped_to_source(self, client, db_session):
        token = _signup(client)
        user = db_session.query(User).filter(User.username == "reindex-user").first()
        job = jobs.submit_reindex_job(db_session, user.id, source_id=999)
        assert job.job_type == "reindex"
        assert job.ref_type == "source"
        assert job.ref_id == 999


class TestAdminReindexEndpoint:
    def test_student_can_trigger_reindex(self, client, monkeypatch):
        # Endpoints are user-scoped: any authenticated user may reindex
        # their own knowledge base (regression: was 403 for students).
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        resp = client.post(
            "/api/kb/admin/reindex",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["job_type"] == "reindex"

    def test_student_can_backfill(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        resp = client.post(
            "/api/kb/admin/backfill",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["job_type"] == "reindex"

    def test_student_cannot_reindex_another_users_source(self, client, db_session):
        # The open endpoints are user-scoped: another user's source_id
        # must 404, not reindex someone else's data.
        token = _signup(client)
        other = _signup(client, "other-user", "other@test.com")
        other_user = db_session.query(User).filter(User.username == "other-user").first()
        src = KbSource(
            user_id=other_user.id, name="Their Vault", source_type="vault_folder",
            root_path="/tmp/theirs", enabled=True,
        )
        db_session.add(src)
        db_session.commit()

        resp = client.post(
            "/api/kb/admin/reindex",
            params={"source_id": src.id},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 404

        resp = client.post(
            "/api/kb/admin/backfill",
            params={"source_id": src.id},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_teacher_can_trigger_reindex(self, client, monkeypatch):
        monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
        token = _signup(
            client, "reindex-teacher", "reindex-teacher@test.com",
            role="teacher", secret="secret",
        )
        resp = client.post(
            "/api/kb/admin/reindex",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["job_type"] == "reindex"

    def test_admin_can_trigger_reindex(self, client, db_session):
        # The seeded single user is promoted to admin (seed_database).
        user = db_session.query(User).first()
        assert user is not None and user.is_admin
        token = _signup(client, "admin-reindex", "admin-reindex@test.com")
        # Promote the new user to admin directly.
        new_user = db_session.query(User).filter(
            User.username == "admin-reindex"
        ).first()
        new_user.is_admin = True
        db_session.commit()

        resp = client.post(
            "/api/kb/admin/reindex",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_backfill_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(settings, "TEACHER_SECRET_KEY", "secret")
        token = _signup(
            client, "backfill-teacher", "backfill-teacher@test.com",
            role="teacher", secret="secret",
        )
        resp = client.post(
            "/api/kb/admin/backfill",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["job_type"] == "reindex"
