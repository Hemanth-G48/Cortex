"""Idea 1 — Knowledge Core data model tests.

Creates every KB model, verifies per-user isolation, the dedupe unique index,
and FK cascades (documents → chunks/versions, source → documents).
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    KbChunk,
    KbDocument,
    KbEdge,
    KbJob,
    KbSource,
    KbTag,
    KbVersion,
    User,
)

USER_A = dict(name="KB A", username="kb-a", email="kb-a@test.com", role="student")
USER_B = dict(name="KB B", username="kb-b", email="kb-b@test.com", role="student")


@pytest.fixture(scope="function")
def kb_engine():
    """Isolated engine with FK enforcement ON for cascade assertions."""
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
def kb_session(kb_engine):
    Session = sessionmaker(bind=kb_engine)
    session = Session()
    yield session
    session.close()


def _user(session, **kwargs) -> User:
    user = User(**kwargs)
    session.add(user)
    session.flush()
    return user


def _doc(session, user, source=None, path="notes/hello.md", content_hash=None) -> KbDocument:
    doc = KbDocument(
        user_id=user.id,
        source_id=source.id if source else None,
        path_rel=path,
        title="Hello",
        doc_type="md",
        content_hash=content_hash,
        status="new",
    )
    session.add(doc)
    session.flush()
    return doc


class TestModelCreation:
    def test_create_all_kb_models(self, kb_session):
        user = _user(kb_session, **USER_A)
        source = KbSource(user_id=user.id, name="Vault", source_type="vault_folder", root_path="/tmp/v")
        kb_session.add(source)
        kb_session.flush()

        doc = _doc(kb_session, user, source)
        chunk = KbChunk(
            user_id=user.id, document_id=doc.id, seq=0, content="c",
            char_start=0, char_end=1, heading_path="H1", token_estimate=1,
        )
        tag = KbTag(user_id=user.id, name="math", kind="inline")
        edge = KbEdge(
            user_id=user.id, source_document_id=doc.id,
            target_document_id=doc.id, relation="DUPLICATE_OF", weight=1.0,
        )
        version = KbVersion(
            user_id=user.id, document_id=doc.id, version_seq=1,
            content_hash="h", snapshot_text="old",
        )
        job = KbJob(user_id=user.id, job_type="scan", status="queued", total_items=1)
        kb_session.add_all([chunk, tag, edge, version, job])
        kb_session.commit()

        assert source.id and doc.id and chunk.id and tag.id and edge.id
        assert version.id and job.id
        # New tables are covered by create_all (no COLUMN_MIGRATIONS entry needed).
        tables = set(Base.metadata.tables.keys())
        for name in ("kb_sources", "kb_documents", "kb_chunks", "kb_tags",
                     "kb_edges", "kb_versions", "kb_jobs"):
            assert name in tables

    def test_tag_name_unique_per_user(self, kb_session):
        ua = _user(kb_session, **USER_A)
        ub = _user(kb_session, **USER_B)
        kb_session.add_all([
            KbTag(user_id=ua.id, name="math"),
            KbTag(user_id=ub.id, name="math"),  # same name, different user → OK
        ])
        kb_session.commit()

        with pytest.raises(Exception):
            kb_session.add(KbTag(user_id=ua.id, name="math"))  # duplicate per user
            kb_session.commit()
        kb_session.rollback()


class TestPerUserIsolation:
    def test_documents_are_scoped_to_user(self, kb_session):
        ua = _user(kb_session, **USER_A)
        ub = _user(kb_session, **USER_B)
        _doc(kb_session, ua, path="a.md", content_hash="aaa")
        _doc(kb_session, ub, path="b.md", content_hash="bbb")
        kb_session.commit()

        a_docs = kb_session.query(KbDocument).filter(KbDocument.user_id == ua.id).all()
        assert [d.path_rel for d in a_docs] == ["a.md"]


class TestFkCascades:
    def test_document_cascade_deletes_chunks_and_versions(self, kb_session):
        user = _user(kb_session, **USER_A)
        doc = _doc(kb_session, user)
        kb_session.add_all([
            KbChunk(user_id=user.id, document_id=doc.id, seq=0, content="x"),
            KbVersion(user_id=user.id, document_id=doc.id, version_seq=1, snapshot_text="s"),
        ])
        kb_session.commit()
        assert kb_session.query(KbChunk).count() == 1
        assert kb_session.query(KbVersion).count() == 1

        kb_session.delete(doc)
        kb_session.commit()
        assert kb_session.query(KbChunk).count() == 0
        assert kb_session.query(KbVersion).count() == 0

    def test_source_cascade_deletes_documents(self, kb_session):
        user = _user(kb_session, **USER_A)
        source = KbSource(user_id=user.id, name="V", root_path="/tmp/v")
        kb_session.add(source)
        kb_session.flush()
        _doc(kb_session, user, source)
        kb_session.commit()
        assert kb_session.query(KbDocument).count() == 1

        kb_session.delete(source)
        kb_session.commit()
        assert kb_session.query(KbDocument).count() == 0

    def test_dedupe_unique_index_blocks_second_same_hash(self, kb_session):
        user = _user(kb_session, **USER_A)
        _doc(kb_session, user, path="one.md", content_hash="same")
        kb_session.commit()

        with pytest.raises(Exception):
            _doc(kb_session, user, path="two.md", content_hash="same")
            kb_session.commit()
        kb_session.rollback()
        # Different users may share identical content.
        ub = _user(kb_session, **USER_B)
        _doc(kb_session, ub, path="two.md", content_hash="same")
        kb_session.commit()
        assert kb_session.query(KbDocument).count() == 2

    def test_null_hashes_are_not_deduplicated(self, kb_session):
        user = _user(kb_session, **USER_A)
        _doc(kb_session, user, path="a.md")
        _doc(kb_session, user, path="b.md")
        kb_session.commit()
        assert kb_session.query(KbDocument).count() == 2

    def test_kb_edge_timestamps_and_defaults(self, kb_session):
        user = _user(kb_session, **USER_A)
        doc = _doc(kb_session, user)
        job = KbJob(user_id=user.id, job_type="scan")
        kb_session.add(job)
        kb_session.commit()
        assert job.status == "queued"
        assert job.processed_items == 0
        assert job.created_at is not None
        assert doc.status == "new"
        assert doc.ocr_used is False
        assert doc.char_count == 0
