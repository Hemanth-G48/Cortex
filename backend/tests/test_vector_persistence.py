"""Vector persistence tests (Second Brain Phase 2, Idea 12, phrase 19).

Exercises the file-backed store across a simulated restart:
embed → write → fresh store instance → load → same ids/vectors.
Also covers idempotency of embed_document_chunks and the
sync_index rebuild path.
"""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    KbChunk,
    KbDocument,
    KbEmbedding,
    KbSource,
    User,
)
from app.services import embeddings
from app.services.kb import KbService
from app.services.kb.embedder import embed_document_chunks, stats, sync_index
from app.services.vector_store_file import FileVectorStore
from app.services.vector_store import VectorStore, get_store
from app.config import settings

USER_A = dict(name="VP A", username="vp-a", email="vp-a@test.com", role="student")


@pytest.fixture(scope="function")
def vp_engine():
    """Isolated engine with FK enforcement ON."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def vp_session(vp_engine):
    Session = sessionmaker(bind=vp_engine)
    session = Session()
    yield session
    session.close()


def _setup_user_doc(vp_session, tmp_dir: str) -> tuple[User, KbDocument]:
    """Create a user + source + document + 3 chunks."""
    user = User(**USER_A)
    vp_session.add(user)
    vp_session.flush()

    source = KbSource(
        user_id=user.id,
        name="test-source",
        source_type="local_dir",
        root_path=tmp_dir,
        enabled=True,
    )
    vp_session.add(source)
    vp_session.flush()

    doc = KbDocument(
        user_id=user.id,
        source_id=source.id,
        path_rel="notes/test.md",
        title="Test Doc",
        doc_type="md",
        extracted_text="Line one.\n\nLine two.\n\nLine three.",
        char_count=30,
        status="unchanged",
        embedding_dirty=True,
    )
    vp_session.add(doc)
    vp_session.flush()

    chunks = []
    for i, text in enumerate(
        ["Line one.", "Line two.", "Line three."]
    ):
        chunk = KbChunk(
            user_id=user.id,
            document_id=doc.id,
            seq=i,
            content=text,
            char_start=i * 10,
            char_end=(i + 1) * 10,
            token_estimate=len(text) // 4,
        )
        vp_session.add(chunk)
        chunks.append(chunk)
    vp_session.flush()
    return user, doc, chunks


class TestFileVectorStorePersistence:
    def test_save_and_load_survives_restart(self, vp_session, tmp_path):
        """Write vectors via one store instance; a fresh instance loads them."""
        # Use a temp dir so the store persists on disk.
        store_dir = str(tmp_path / "kb_index")

        store1 = FileVectorStore(directory=store_dir)
        store1.add(["chunk:1", "chunk:2"], [[1.0, 0.0], [0.0, 1.0]])
        assert len(store1) == 2

        # Simulate restart: construct a fresh instance pointing at same dir.
        store2 = FileVectorStore(directory=store_dir)
        assert len(store2) == 2

        results = store2.query([1.0, 0.0], k=2)
        result_ids = [r["id"] for r in results]
        assert "chunk:1" in result_ids
        assert "chunk:2" in result_ids

    def test_fresh_store_with_no_files_is_empty(self, tmp_path):
        """A store with no existing files starts empty."""
        store_dir = str(tmp_path / "empty_index")
        store = FileVectorStore(directory=store_dir)
        assert len(store) == 0
        assert store.query([1.0, 0.0], k=1) == []

    def test_corrupt_files_fallback_to_empty(self, tmp_path):
        """Corrupt .npy or ids.json is ignored; store starts empty."""
        store_dir = str(tmp_path / "corrupt_index")
        os.makedirs(store_dir, exist_ok=True)
        # Write a corrupt numpy file.
        with open(os.path.join(store_dir, "vectors.npy"), "wb") as f:
            f.write(b"not a numpy file")
        with open(os.path.join(store_dir, "ids.json"), "w") as f:
            f.write("not json")

        store = FileVectorStore(directory=store_dir)
        assert len(store) == 0

    def test_add_replace_and_delete_persist(self, tmp_path):
        """Add, replace, delete — all persisted across restarts."""
        store_dir = str(tmp_path / "mutate_index")
        store1 = FileVectorStore(directory=store_dir)
        store1.add(["a", "b"], [[1.0, 0.0], [0.0, 1.0]])

        store2 = FileVectorStore(directory=store_dir)
        assert len(store2) == 2

        # Replace 'a'.
        store2.add(["a"], [[0.0, 1.0]])
        store3 = FileVectorStore(directory=store_dir)
        results = store3.query([0.0, 1.0], k=2)
        assert results[0]["id"] == "a"

        # Delete 'b'.
        store3.delete(["b"])
        store4 = FileVectorStore(directory=store_dir)
        assert len(store4) == 1
        assert store4.query([0.0, 1.0], k=1)[0]["id"] == "a"


class TestEmbedDocumentChunks:
    def test_embeds_chunks_and_writes_rows(self, vp_session, tmp_path):
        """embed_document_chunks writes KbEmbedding rows with local model."""
        user, doc, chunks = _setup_user_doc(vp_session, str(tmp_path))
        vp_session.commit()

        result = embed_document_chunks(vp_session, user.id, doc.id)
        assert result["total"] == 3
        assert result["embedded"] == 3
        assert result["skipped"] == 0

        rows = (
            vp_session.query(KbEmbedding)
            .filter(KbEmbedding.user_id == user.id)
            .all()
        )
        assert len(rows) == 3
        for row in rows:
            assert row.model == embeddings.LOCAL_MODEL
            assert row.dim == settings.EMBEDDINGS_DIM
            vec = KbService.json_loads(row.vector)
            assert isinstance(vec, list)
            assert len(vec) == settings.EMBEDDINGS_DIM

        # Doc flag cleared.
        assert doc.embedding_dirty is False

    def test_idempotent_rerun_skips_already_embedded(self, vp_session, tmp_path):
        """Re-running embed_document_chunks skips cached chunks."""
        user, doc, chunks = _setup_user_doc(vp_session, str(tmp_path))
        vp_session.commit()

        result1 = embed_document_chunks(vp_session, user.id, doc.id)
        assert result1["embedded"] == 3

        result2 = embed_document_chunks(vp_session, user.id, doc.id)
        assert result2["embedded"] == 0
        assert result2["skipped"] == 3
        assert result2["total"] == 3

    def test_empty_doc_has_no_embeddings(self, vp_session, tmp_path):
        """Document with no chunks returns zero counts."""
        user = User(**USER_A)
        vp_session.add(user)
        vp_session.flush()

        source = KbSource(
            user_id=user.id,
            name="empty-source",
            source_type="local_dir",
            root_path=str(tmp_path),
            enabled=True,
        )
        vp_session.add(source)
        vp_session.flush()

        doc = KbDocument(
            user_id=user.id,
            source_id=source.id,
            path_rel="notes/empty.md",
            title="Empty",
            doc_type="md",
            extracted_text="",
            char_count=0,
            status="unchanged",
        )
        vp_session.add(doc)
        vp_session.flush()

        result = embed_document_chunks(vp_session, user.id, doc.id)
        assert result["total"] == 0
        assert result["embedded"] == 0
        assert result["skipped"] == 0


class TestSyncIndex:
    def test_sync_index_rebuilds_store(self, vp_session, tmp_path, monkeypatch):
        """sync_index loads vectors from db into a file store."""
        user, doc, chunks = _setup_user_doc(vp_session, str(tmp_path))
        vp_session.commit()

        embed_document_chunks(vp_session, user.id, doc.id)

        store_dir = str(tmp_path / "sync_index")
        fresh_store = FileVectorStore(directory=store_dir)

        # Patch get_store so sync_index uses our file store.
        monkeypatch.setattr(
            "app.services.kb.embedder.get_store", lambda: fresh_store
        )

        result = sync_index(vp_session, user.id)
        assert result["vectors"] == 3
        assert result["dim"] == settings.EMBEDDINGS_DIM

        # A fresh file store at the same dir should have the data.
        verify_store = FileVectorStore(directory=store_dir)
        assert len(verify_store) == 3

    def test_sync_index_is_idempotent(self, vp_session, tmp_path, monkeypatch):
        """Calling sync_index twice produces the same result."""
        user, doc, chunks = _setup_user_doc(vp_session, str(tmp_path))
        vp_session.commit()

        embed_document_chunks(vp_session, user.id, doc.id)

        store_dir = str(tmp_path / "sync_index")
        fresh_store = FileVectorStore(directory=store_dir)
        monkeypatch.setattr(
            "app.services.kb.embedder.get_store", lambda: fresh_store
        )

        result1 = sync_index(vp_session, user.id)
        result2 = sync_index(vp_session, user.id)
        assert result1["vectors"] == result2["vectors"]


class TestStats:
    def test_stats_returns_correct_counts(self, vp_session, tmp_path):
        """stats() returns per-user counts matching the db."""
        user, doc, chunks = _setup_user_doc(vp_session, str(tmp_path))
        vp_session.commit()

        result = embed_document_chunks(vp_session, user.id, doc.id)
        vp_session.refresh(doc)

        stats_result = stats(vp_session, user.id)
        assert stats_result["document_count"] == 1
        assert stats_result["chunk_count"] == 3
        assert stats_result["embedding_count"] == 3
        assert stats_result["embedded_documents"] == 1
        assert stats_result["tag_count"] == 0
        assert stats_result["edge_count"] == 0
        assert stats_result["duplicate_count"] == 0
        assert stats_result["total_tokens"] == 6  # 3 chunks, ~2 tokens each
        assert stats_result["dirty_documents"] == 0  # embedding_dirty cleared

    def test_stats_counts_dirty_documents(self, vp_session, tmp_path):
        """Dirty documents are counted when embedding_dirty=True."""
        user = User(**USER_A)
        vp_session.add(user)
        vp_session.flush()

        source = KbSource(
            user_id=user.id,
            name="dirty-source",
            source_type="local_dir",
            root_path=str(tmp_path),
            enabled=True,
        )
        vp_session.add(source)
        vp_session.flush()

        doc = KbDocument(
            user_id=user.id,
            source_id=source.id,
            path_rel="notes/dirty.md",
            title="Dirty",
            doc_type="md",
            extracted_text="Some text.",
            char_count=10,
            embedding_dirty=True,
        )
        vp_session.add(doc)
        vp_session.flush()

        stats_result = stats(vp_session, user.id)
        assert stats_result["dirty_documents"] == 1
        assert stats_result["document_count"] == 1
        assert stats_result["chunk_count"] == 0