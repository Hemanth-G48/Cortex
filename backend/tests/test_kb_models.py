"""Idea 1 — Knowledge Core data model tests.

Creates every KB model, verifies per-user isolation, the dedupe unique index,
and FK cascades (documents → chunks/versions, source → documents).
"""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, text
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


class TestColumnMigrations:
    """Regression coverage for ``migrate_schema`` — columns added to models
    after a table first shipped must be back-filled on legacy databases."""

    @staticmethod
    def _legacy_engine(extra: dict[str, str]) -> tuple:
        """A legacy engine containing a minimal table for every table the
        migration registry touches, plus the caller's extra tables (name →
        column DDL). SQLite returns an empty result for PRAGMA on a missing
        table, so without the stubs ``migrate_schema`` would ALTER missing
        tables."""
        import app.database as database

        legacy = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with legacy.begin() as conn:
            # Stub tables so every registered migration finds its table (the
            # caller's tables are created with their legacy DDL instead). NOTE:
            # stubs only work because migrate_schema() applies the COLUMN_-
            # MIGRATIONS ALTERs before the index/rebuild helpers run — keep it
            # that way if new helpers are added.
            for table in database.COLUMN_MIGRATIONS:
                if table in extra:
                    continue
                conn.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            for table, ddl in extra.items():
                conn.execute(text(f"CREATE TABLE {table} ({ddl})"))
        return legacy, database

    def test_legacy_learning_plans_gains_source_json(self, monkeypatch):
        """The two-layer Learning Path Planner added ``learning_plans.source_json``
        to the model. A DB created before that must gain the column on startup
        (this was the cause of a live ``API 500`` — ``plan_dict`` read
        ``plan.source_json`` against a table lacking it)."""
        legacy, database = self._legacy_engine(
            {
                # Mirrors the real pre-feature table exactly: every model column
                # except the Layer-1 ``source_json`` (the only drift found on a
                # live DB that produced this 500).
                "learning_plans": (
                    "id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
                    "goal VARCHAR(300) NOT NULL, goal_key VARCHAR(60), "
                    "description TEXT, resources_json TEXT, knowledge_json TEXT, "
                    "plan_json TEXT, status VARCHAR(20) DEFAULT 'draft', "
                    "engine VARCHAR(20) DEFAULT 'deterministic', "
                    "created_at DATETIME, generated_at DATETIME"
                )
            }
        )
        with legacy.begin() as conn:
            conn.execute(
                text("INSERT INTO learning_plans (user_id, goal) VALUES (1, 'websecurity')")
            )

        monkeypatch.setattr(database, "engine", legacy)
        database.migrate_schema()

        def _cols():
            with legacy.connect() as conn:
                return {
                    row[1]
                    for row in conn.execute(text("PRAGMA table_info(learning_plans)")).fetchall()
                }

        assert "source_json" in _cols(), "source_json must be added to legacy tables"
        # The exact failure mode of the live API 500: loading the row through
        # the ORM model (as plan_dict does) must now work on the migrated
        # legacy row — without the migration this raises OperationalError
        # (no such column: learning_plans.source_json).
        from sqlalchemy.orm import sessionmaker
        from app.models import LearningPlan

        LegacySession = sessionmaker(bind=legacy)
        session = LegacySession()
        plan = session.query(LearningPlan).filter_by(goal="websecurity").first()
        assert plan is not None
        assert plan.source_json is None  # readable via the model → no 500
        session.close()
        # Idempotent: a second run must not error and must not duplicate.
        database.migrate_schema()
        assert "source_json" in _cols()
        with legacy.connect() as conn:
            rows = conn.execute(text("SELECT COUNT(*) FROM learning_plans")).fetchone()[0]
        assert rows == 1  # preserved the legacy row

    def test_learning_tasks_gain_resource_and_path_links(self, monkeypatch):
        """learning_tasks.resource_id/path_id were also added post-ship; the
        migration must back-fill them too."""
        legacy, database = self._legacy_engine(
            {
                "learning_tasks": (
                    "id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL, "
                    "user_id INTEGER NOT NULL, title VARCHAR(300) NOT NULL, "
                    "done BOOLEAN DEFAULT 0"
                )
            }
        )
        monkeypatch.setattr(database, "engine", legacy)
        database.migrate_schema()

        with legacy.connect() as conn:
            cols = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(learning_tasks)")).fetchall()
            }
        assert "resource_id" in cols
        assert "path_id" in cols


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
