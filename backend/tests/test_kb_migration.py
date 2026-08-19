"""Second Brain migration tests — notes/ + daily-life/ separation.

The non-negotiable rule under test: **changing a file's path is not changing
its content**. Moving an unchanged note into ``notes/`` must reuse the same
document id, the same chunks and the same embeddings — zero new embeddings.

Also covers: daily-life exclusion, incremental resync semantics, the ``local``
external-vault adapter (Copy Recent Notes), and the cross-user duplicate
source handling.
"""

from __future__ import annotations

import os
import shutil

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Course, KbChunk, KbDocument, KbEmbedding, KbJob, KbSource, User
from app.services.kb import auto_sync
from app.services.kb.embedder import embed_document_chunks
from app.services.kb.migrate import (
    disable_cross_user_duplicates,
    purge_source,
    repoint_source_roots,
    run_migration,
)
from app.services.kb.scanner import scan_and_ingest


def _user(db: Session, username: str = "mig-user") -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is not None:
        return user
    user = User(name=username, username=username, email=f"{username}@test.com", role="student")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_source(db: Session, user_id: int, root, *, sync_type: str = "none", sync_source_path=None) -> KbSource:
    src = KbSource(
        user_id=user_id,
        name="notes",
        source_type="vault_folder",
        root_path=str(root),
        enabled=True,
        sync_type=sync_type,
        sync_source_path=sync_source_path,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def _embed(db: Session, user_id: int, doc: KbDocument) -> dict:
    return embed_document_chunks(db, user_id, doc.id)


def _embedding_count(db: Session, user_id: int) -> int:
    return db.query(KbEmbedding).filter(KbEmbedding.user_id == user_id).count()


def _chunk_ids(db: Session, doc_id: int) -> list[int]:
    return [c.id for c in db.query(KbChunk).filter(KbChunk.document_id == doc_id).order_by(KbChunk.seq).all()]


def _doc_by_path(db: Session, source_id: int, path_rel: str) -> KbDocument | None:
    return (
        db.query(KbDocument)
        .filter(KbDocument.source_id == source_id, KbDocument.path_rel == path_rel)
        .first()
    )


# ---------------------------------------------------------------------------
# Core rule: path changes never re-embed
# ---------------------------------------------------------------------------

class TestMoveReusesEverything:
    def test_path_only_move_reuses_document_chunks_and_embeddings(self, db_session, tmp_path):
        """Move a note to another folder with identical content → same doc id,
        same chunks, same embeddings, path updated. Zero new embeddings."""
        uid = _user(db_session).id
        (tmp_path / "Cybersecurity").mkdir()
        (tmp_path / "Reverse Engineering").mkdir()
        (tmp_path / "Cybersecurity" / "SSRF.md").write_text("# SSRF\n\nServer-side request forgery notes.")
        src = _make_source(db_session, uid, tmp_path)

        scan_and_ingest(db_session, src.id)
        doc = _doc_by_path(db_session, src.id, "Cybersecurity/SSRF.md")
        assert doc is not None and doc.status == "unchanged"
        doc_id = doc.id
        chunks_before = _chunk_ids(db_session, doc_id)
        assert chunks_before, "document must be chunked"
        _embed(db_session, uid, doc)
        emb_before = _embedding_count(db_session, uid)
        assert emb_before > 0

        # Move the file: Cybersecurity/SSRF.md → Reverse Engineering/SSRF.md
        shutil.move(
            str(tmp_path / "Cybersecurity" / "SSRF.md"),
            str(tmp_path / "Reverse Engineering" / "SSRF.md"),
        )

        summary = scan_and_ingest(db_session, src.id)
        assert summary["moved"] == 1
        assert summary["added"] == 0
        assert summary["changed"] == 0
        assert summary["removed"] == 0

        db_session.expire_all()
        moved = _doc_by_path(db_session, src.id, "Reverse Engineering/SSRF.md")
        assert moved is not None
        assert moved.id == doc_id  # same document identity
        assert moved.path_rel == "Reverse Engineering/SSRF.md"
        assert moved.file_path == str(tmp_path / "Reverse Engineering" / "SSRF.md")
        assert _chunk_ids(db_session, doc_id) == chunks_before  # same chunks
        assert _embedding_count(db_session, uid) == emb_before  # embeddings reused
        # Old path no longer resolves to a live row.
        assert _doc_by_path(db_session, src.id, "Cybersecurity/SSRF.md") is None

    def test_move_within_scan_order_is_idempotent(self, db_session, tmp_path):
        """Walking order must not matter: a second scan after the move still
        reports everything unchanged (no duplicate, no re-embed)."""
        uid = _user(db_session).id
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "x.md").write_text("same content everywhere")
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)
        doc = _doc_by_path(db_session, src.id, "a/x.md")
        _embed(db_session, uid, doc)
        emb_before = _embedding_count(db_session, uid)

        shutil.move(str(tmp_path / "a" / "x.md"), str(tmp_path / "b" / "x.md"))
        first = scan_and_ingest(db_session, src.id)
        assert first["moved"] == 1
        second = scan_and_ingest(db_session, src.id)
        assert second["moved"] == 0
        assert second["unchanged"] == 1
        assert second["added"] == 0
        assert _embedding_count(db_session, uid) == emb_before

    def test_genuine_duplicate_still_dedupes(self, db_session, tmp_path):
        """Two files with identical content that BOTH exist are duplicates,
        not moves — the stable dedupe path must keep working."""
        uid = _user(db_session).id
        (tmp_path / "one.md").write_text("# Dup\ncontent")
        (tmp_path / "two.md").write_text("# Dup\ncontent")
        src = _make_source(db_session, uid, tmp_path)

        summary = scan_and_ingest(db_session, src.id)
        assert summary["added"] == 1
        assert summary["duplicates_found"] == 1
        assert summary["moved"] == 0


class TestIncrementalSync:
    def test_new_file_embeds(self, db_session, tmp_path):
        uid = _user(db_session).id
        (tmp_path / "a.md").write_text("# A\ncontent a")
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)
        before = _embedding_count(db_session, uid)

        (tmp_path / "b.md").write_text("# B\ncontent b")
        summary = scan_and_ingest(db_session, src.id)
        assert summary["added"] == 1 and summary["unchanged"] == 1
        doc_b = _doc_by_path(db_session, src.id, "b.md")
        _embed(db_session, uid, doc_b)
        assert _embedding_count(db_session, uid) == before + 1  # 1 chunk each

    def test_modified_file_replaces_stale_embeddings(self, db_session, tmp_path):
        uid = _user(db_session).id
        (tmp_path / "a.md").write_text("# A\nshort version")
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)
        doc = _doc_by_path(db_session, src.id, "a.md")
        _embed(db_session, uid, doc)
        old_chunk_ids = set(_chunk_ids(db_session, doc.id))
        assert old_chunk_ids

        (tmp_path / "a.md").write_text("# A\nmuch longer content " + "words " * 400)
        summary = scan_and_ingest(db_session, src.id)
        assert summary["changed"] == 1

        db_session.expire_all()
        new_chunk_ids = set(_chunk_ids(db_session, doc.id))
        assert new_chunk_ids
        # Re-chunking replaced the old chunks (SQLite may reuse physical ids,
        # so the guarantee is about *embedding rows*: none may survive from
        # the superseded content). Immediately after the change, before any
        # re-embed, the document must have zero embeddings.
        doc_emb = (
            db_session.query(KbEmbedding)
            .join(KbChunk, KbEmbedding.chunk_id == KbChunk.id)
            .filter(KbChunk.document_id == doc.id, KbEmbedding.user_id == uid)
            .count()
        )
        assert doc_emb == 0  # old embeddings removed with their chunks

        _embed(db_session, uid, doc)
        live = (
            db_session.query(KbEmbedding)
            .join(KbChunk, KbEmbedding.chunk_id == KbChunk.id)
            .filter(KbChunk.document_id == doc.id, KbEmbedding.user_id == uid)
            .count()
        )
        assert live == len(new_chunk_ids)  # fresh embeddings for the new content

    def test_deleted_file_swept(self, db_session, tmp_path):
        uid = _user(db_session).id
        (tmp_path / "a.md").write_text("# A\ncontent")
        (tmp_path / "b.md").write_text("# B\ncontent")
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)

        (tmp_path / "b.md").unlink()
        summary = scan_and_ingest(db_session, src.id)
        assert summary["removed"] == 1
        db_session.expire_all()
        doc_b = _doc_by_path(db_session, src.id, "b.md")
        assert doc_b is not None and doc_b.status == "deleted"
        doc_a = _doc_by_path(db_session, src.id, "a.md")
        assert doc_a.status == "unchanged"

    def test_resync_no_changes_is_all_unchanged(self, db_session, tmp_path):
        uid = _user(db_session).id
        (tmp_path / "x.md").write_text("# X\ncontent")
        (tmp_path / "y.md").write_text("# Y\ncontent")
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)
        summary = scan_and_ingest(db_session, src.id)
        assert summary["added"] == 0 and summary["changed"] == 0
        assert summary["moved"] == 0 and summary["removed"] == 0
        assert summary["unchanged"] == 2

    def test_duplicate_filenames_in_different_folders_are_separate(self, db_session, tmp_path):
        uid = _user(db_session).id
        (tmp_path / "Web Security").mkdir()
        (tmp_path / "Reverse Engineering").mkdir()
        (tmp_path / "Web Security" / "Authentication.md").write_text("web auth notes")
        (tmp_path / "Reverse Engineering" / "Authentication.md").write_text("RE auth notes")
        src = _make_source(db_session, uid, tmp_path)

        scan_and_ingest(db_session, src.id)
        docs = (
            db_session.query(KbDocument)
            .filter(KbDocument.source_id == src.id)
            .all()
        )
        assert len(docs) == 2  # same filename, different paths → separate documents


# ---------------------------------------------------------------------------
# daily-life separation
# ---------------------------------------------------------------------------

class TestDailyLife:
    def test_daily_life_outside_notes_root_is_not_scanned(self, db_session, tmp_path):
        """With the source rooted at ``notes/`` (post-migration layout), a
        sibling ``daily-life/`` folder is structurally invisible to the KB."""
        uid = _user(db_session).id
        notes = tmp_path / "notes"
        daily = tmp_path / "daily-life"
        (notes / "Cybersecurity").mkdir(parents=True)
        (daily).mkdir()
        (notes / "Cybersecurity" / "SSRF.md").write_text("# SSRF\nnotes")
        (daily / "personal-journal.md").write_text("# Day log\nnon-knowledge")

        src = _make_source(db_session, uid, notes)
        summary = scan_and_ingest(db_session, src.id)
        assert summary["files_seen"] == 1  # daily-life never seen
        assert _doc_by_path(db_session, src.id, "personal-journal.md") is None

    def test_scanner_skips_root_level_daily_life_folder(self, db_session, tmp_path):
        """Even when a source is rooted at the vault root (pre-migration
        layout), a top-level ``daily-life`` folder is excluded."""
        uid = _user(db_session).id
        (tmp_path / "daily-life").mkdir()
        (tmp_path / "daily-life" / "log.md").write_text("# Log\nstuff")
        (tmp_path / "knowledge.md").write_text("# Knowledge\nstuff")
        src = _make_source(db_session, uid, tmp_path)

        summary = scan_and_ingest(db_session, src.id)
        assert summary["files_seen"] == 1
        assert _doc_by_path(db_session, src.id, "knowledge.md") is not None
        assert _doc_by_path(db_session, src.id, "daily-life/log.md") is None


# ---------------------------------------------------------------------------
# Migration orchestration
# ---------------------------------------------------------------------------

class TestMigration:
    def test_full_migration_causes_zero_reembedding(self, db_session, tmp_path):
        """Move top-level folders into notes/, repoint the source root → the
        scan sees zero changes and reuses every existing embedding."""
        uid = _user(db_session).id
        vault = tmp_path / "second_brain"
        (vault / "Cybersecurity" / "Web Security").mkdir(parents=True)
        (vault / "Programming").mkdir()
        (vault / "Cybersecurity" / "Web Security" / "SSRF.md").write_text("# SSRF\nlong ssrf notes " * 40)
        (vault / "Programming" / "basics.md").write_text("# Basics\npython basics " * 40)
        src = _make_source(db_session, uid, vault)

        scan_and_ingest(db_session, src.id)
        docs = db_session.query(KbDocument).filter(KbDocument.source_id == src.id).all()
        assert len(docs) == 2
        for doc in docs:
            _embed(db_session, uid, doc)
        emb_before = _embedding_count(db_session, uid)
        assert emb_before > 0

        # Run the real migration orchestration: reorganize → repoint →
        # refresh file paths → rescan.
        report = run_migration(db_session, str(vault), backup=False, scan=True)

        assert (vault / "notes" / "Cybersecurity" / "Web Security" / "SSRF.md").exists()
        assert (vault / "notes" / "Programming" / "basics.md").exists()
        assert (vault / "daily-life").is_dir()
        assert not (vault / "Cybersecurity").exists()
        assert report["sources"]["repointed"][0]["new_root"] == str(vault / "notes")
        assert report["sources"]["file_paths_refreshed"] == 2

        summary = report["scan"]
        assert summary["added"] == 0 and summary["changed"] == 0
        assert summary["moved"] == 0 and summary["removed"] == 0
        assert summary["unchanged"] == 2  # every note recognized, none re-embedded

        db_session.expire_all()
        assert _embedding_count(db_session, uid) == emb_before  # 0 new embeddings
        # Absolute file paths refreshed to the new location (ingest-ready).
        for doc in db_session.query(KbDocument).filter(KbDocument.source_id == src.id).all():
            assert doc.file_path.startswith(str(vault / "notes"))

    def test_run_migration_dry_run_moves_nothing(self, db_session, tmp_path):
        uid = _user(db_session).id
        vault = tmp_path / "second_brain"
        (vault / "Cybersecurity").mkdir(parents=True)
        (vault / "Cybersecurity" / "a.md").write_text("# A\ncontent")
        _make_source(db_session, uid, vault)

        report = run_migration(db_session, str(vault), backup=False, scan=False, dry_run=True)
        assert report["dry_run"] is True
        assert report["reorganize"]["moved_dirs"] == 1
        assert (vault / "Cybersecurity").exists()  # nothing moved
        assert not (vault / "notes").exists()

    def test_repoint_is_idempotent(self, db_session, tmp_path):
        uid = _user(db_session).id
        vault = tmp_path / "vault"
        notes = vault / "notes"
        notes.mkdir(parents=True)
        src = _make_source(db_session, uid, notes)
        # Already rooted at notes/ → no repoint entry.
        repointed = repoint_source_roots(db_session, str(vault))
        assert repointed["repointed"] == []
        db_session.refresh(src)
        assert src.root_path == str(notes)

    def test_cross_user_duplicate_sources_disabled_not_deleted(self, db_session, tmp_path):
        """Two sources on the same vault from different users: the later one
        is disabled (watcher stops double-scanning) — nothing is deleted."""
        vault = tmp_path / "vault"
        vault.mkdir()
        user_a = _user(db_session, "user-a")
        user_b = _user(db_session, "user-b")
        src_a = _make_source(db_session, user_a.id, vault)
        src_b = _make_source(db_session, user_b.id, vault)

        result = disable_cross_user_duplicates(db_session, str(vault))
        assert result["kept"] == src_a.id
        assert [d["id"] for d in result["disabled"]] == [src_b.id]
        db_session.refresh(src_a)
        db_session.refresh(src_b)
        assert src_a.enabled is True
        assert src_b.enabled is False  # disabled, not deleted
        assert db_session.query(KbSource).count() == 2

    def test_same_user_sources_not_disabled(self, db_session, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        uid = _user(db_session).id
        _make_source(db_session, uid, vault)
        _make_source(db_session, uid, vault)
        result = disable_cross_user_duplicates(db_session, str(vault))
        assert result["disabled"] == []  # same owner → both stay enabled


# ---------------------------------------------------------------------------
# Local external-vault sync ("Copy Recent Notes")
# ---------------------------------------------------------------------------

class TestLocalSync:
    def test_copies_only_knowledge_deltas_and_never_reembeds(self, db_session, tmp_path):
        uid = _user(db_session).id
        external = tmp_path / "external-vault"
        notes = tmp_path / "notes"
        notes.mkdir()
        (external / "Cybersecurity").mkdir(parents=True)
        (external / "daily-life").mkdir()
        (external / ".obsidian").mkdir()
        (external / "Cybersecurity" / "SSRF.md").write_text("# SSRF\nssrf notes " * 30)
        (external / "daily-life" / "log.md").write_text("# Log\nprivate")
        (external / ".obsidian" / "config.json").write_text("{}")

        src = _make_source(
            db_session, uid, notes, sync_type="local", sync_source_path=str(external)
        )

        first = auto_sync.sync_source(db_session, src, force=True)
        assert first["copied"] == 1  # only SSRF.md — daily-life + noise skipped
        assert (notes / "Cybersecurity" / "SSRF.md").exists()
        assert not (notes / "daily-life").exists()
        assert not (notes / ".obsidian").exists()
        doc = _doc_by_path(db_session, src.id, "Cybersecurity/SSRF.md")
        assert doc is not None and doc.status == "unchanged"
        _embed(db_session, uid, doc)
        emb_before = _embedding_count(db_session, uid)

        # Second sync: nothing changed → no copy, no re-embed.
        second = auto_sync.sync_source(db_session, src, force=True)
        assert second["copied"] == 0
        assert second["unchanged"] == 1
        assert _embedding_count(db_session, uid) == emb_before

        # External edit → exactly that file is re-copied and re-indexed.
        (external / "Cybersecurity" / "SSRF.md").write_text("# SSRF\nupdated notes " * 30)
        third = auto_sync.sync_source(db_session, src, force=True)
        assert third["copied"] == 1
        db_session.refresh(doc)
        assert doc.status == "unchanged"

        # External deletion of a previously-synced file → the copy is removed
        # and the index sweeps it (row stays, status → deleted, so an identical
        # file coming back later can resurrect without re-embedding).
        (external / "Cybersecurity" / "SSRF.md").unlink()
        fourth = auto_sync.sync_source(db_session, src, force=True)
        assert fourth["removed"] == 1
        assert not (notes / "Cybersecurity" / "SSRF.md").exists()
        swept = _doc_by_path(db_session, src.id, "Cybersecurity/SSRF.md")
        assert swept is not None and swept.status == "deleted"

    def test_local_sync_requires_configured_source(self, db_session, tmp_path):
        uid = _user(db_session).id
        notes = tmp_path / "notes"
        notes.mkdir()
        src = _make_source(db_session, uid, notes, sync_type="local")  # no sync_source_path
        result = auto_sync.sync_source(db_session, src, force=True)
        assert result["skipped"] is True
        assert "sync_source_path" in result["reason"]

    def test_scheduled_local_sync_gated_by_own_toggle(self, db_session, tmp_path, monkeypatch):
        """force=False (the scheduled path) must gate on KB_AUTO_LOCAL_SYNC_ENABLED
        — NOT KB_SYNC_ENABLED — so Copy Recent Notes has its own timer toggle."""
        uid = _user(db_session).id
        external = tmp_path / "external-vault"
        external.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        (external / "x.md").write_text("# X\ncontent")
        src = _make_source(
            db_session, uid, notes, sync_type="local", sync_source_path=str(external)
        )

        monkeypatch.setattr(settings, "KB_AUTO_LOCAL_SYNC_ENABLED", False)
        monkeypatch.setattr(settings, "KB_SYNC_ENABLED", True)  # must NOT matter
        skipped = auto_sync.sync_source(db_session, src, force=False)
        assert skipped["skipped"] is True
        assert "KB_AUTO_LOCAL_SYNC_ENABLED" in skipped["reason"]
        assert not (notes / "x.md").exists()

        monkeypatch.setattr(settings, "KB_AUTO_LOCAL_SYNC_ENABLED", True)
        ran = auto_sync.sync_source(db_session, src, force=False)
        assert ran["copied"] == 1
        assert (notes / "x.md").exists()


class TestScheduledLocalSyncJob:
    """The dedicated ``auto_local_sync`` automation job (Copy Recent Notes on
    a timer) — registered with its own toggle, disjoint from the git/drive/clip
    job, and driven by the watcher's periodic automation pass."""

    def test_job_registered_with_dedicated_toggle(self):
        from app.services.kb import automation

        jobs = {j["name"]: j for j in automation.registered_jobs()}
        assert "auto_local_sync" in jobs
        assert jobs["auto_local_sync"]["toggle"] == "KB_AUTO_LOCAL_SYNC_ENABLED"

    def test_auto_sync_run_excludes_local_sources(self, db_session, tmp_path):
        """The git/drive/clip job must never double-sync a local vault — local
        sources belong exclusively to auto_local_sync."""
        uid = _user(db_session).id
        external = tmp_path / "external-vault"
        external.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        (external / "x.md").write_text("# X\ncontent")
        _make_source(
            db_session, uid, notes, sync_type="local", sync_source_path=str(external)
        )
        result = auto_sync.run(db_session, uid)
        assert result["sources"] == 0  # local sources not in scope
        assert not (notes / "x.md").exists()

    def test_run_local_syncs_only_local_sources(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "KB_AUTO_LOCAL_SYNC_ENABLED", True)
        uid = _user(db_session).id
        external = tmp_path / "external-vault"
        notes = tmp_path / "notes"
        notes.mkdir()
        (external / "Cybersecurity").mkdir(parents=True)
        (external / "Cybersecurity" / "SSRF.md").write_text("# SSRF\nssrf notes " * 30)
        _make_source(
            db_session, uid, notes, sync_type="local", sync_source_path=str(external)
        )
        # A git source must not be touched by the local job.
        git_root = tmp_path / "git-repo"
        git_root.mkdir()
        _make_source(db_session, uid, git_root, sync_type="git")

        result = auto_sync.run_local(db_session, uid)
        assert result["sources"] == 1  # only the local source
        assert result["copied"] == 1
        assert (notes / "Cybersecurity" / "SSRF.md").exists()

    def test_job_runs_through_automation_gate_and_audits(self, db_session, tmp_path, monkeypatch):
        """Full loop: automation.run_one gates on the toggle, runs the job
        inline (hermetic), and persists an auditable kb_jobs row."""
        from app.services.kb import automation

        uid = _user(db_session).id
        external = tmp_path / "external-vault"
        external.mkdir()
        notes = tmp_path / "notes"
        notes.mkdir()
        (external / "a.md").write_text("# A\ncontent alpha " * 30)
        _make_source(
            db_session, uid, notes, sync_type="local", sync_source_path=str(external)
        )

        monkeypatch.setattr(settings, "KB_AUTO_LOCAL_SYNC_ENABLED", False)
        skipped = automation.run_one(db_session, uid, "auto_local_sync")
        assert skipped["skipped"] is True
        assert not (notes / "a.md").exists()

        monkeypatch.setattr(settings, "KB_AUTO_LOCAL_SYNC_ENABLED", True)
        ran = automation.run_one(db_session, uid, "auto_local_sync")
        assert ran["status"] == "done"
        assert (notes / "a.md").exists()
        row = (
            db_session.query(KbJob)
            .filter(KbJob.ref_type == "auto_local_sync")
            .order_by(KbJob.id.desc())
            .first()
        )
        assert row is not None and row.status == "done"

    def test_watcher_automation_pass_fires_on_interval(self, db_session, tmp_path, monkeypatch):
        """The watcher's periodic pass calls automation.run_all per user with an
        enabled source, at most once per KB_AUTO_RUN_INTERVAL_SECONDS."""
        from app.services.kb import automation
        from app.services.kb import watcher as watcher_mod

        calls: list = []
        monkeypatch.setattr(settings, "KB_AUTO_RUN_INTERVAL_SECONDS", 60)
        monkeypatch.setattr(watcher_mod, "_auto_last_run", 0.0)  # last run long ago
        monkeypatch.setattr(
            automation, "run_all", lambda db, user_id, force=False: calls.append(user_id)
        )

        # No enabled sources → the pass is a no-op (but still stamps the timer).
        watcher_mod._maybe_run_automations(lambda: db_session)
        assert calls == []

        # One enabled source, interval elapsed → fires exactly once for its user.
        uid = _user(db_session).id
        _make_source(db_session, uid, tmp_path)
        watcher_mod._auto_last_run = 0.0
        watcher_mod._maybe_run_automations(lambda: db_session)
        assert calls == [uid]

        # Second call within the interval → skipped (timer, not per-poll).
        watcher_mod._maybe_run_automations(lambda: db_session)
        assert calls == [uid]

        # After the interval elapses → fires again.
        watcher_mod._auto_last_run = 0.0
        watcher_mod._maybe_run_automations(lambda: db_session)
        assert calls == [uid, uid]

    def test_disabled_interval_never_fires(self, db_session, tmp_path, monkeypatch):
        from app.services.kb import automation
        from app.services.kb import watcher as watcher_mod

        calls: list = []
        monkeypatch.setattr(settings, "KB_AUTO_RUN_INTERVAL_SECONDS", 0)
        monkeypatch.setattr(watcher_mod, "_auto_last_run", 0.0)
        monkeypatch.setattr(
            automation, "run_all", lambda db, user_id, force=False: calls.append(user_id)
        )
        uid = _user(db_session).id
        _make_source(db_session, uid, tmp_path)

        watcher_mod._maybe_run_automations(lambda: db_session)
        assert calls == []


class TestPurgeSource:
    def test_purge_removes_source_and_all_index_rows(self, db_session, tmp_path):
        """Hard-delete a source: docs/chunks/embeddings/edges/folders gone,
        other users' data untouched, linked courses detached."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "a.md").write_text("# A\ncontent alpha " * 30)
        (vault / "b.md").write_text("# B\ncontent beta " * 30)
        user_a = _user(db_session, "purge-a")
        user_b = _user(db_session, "purge-b")
        src_a = _make_source(db_session, user_a.id, vault)
        src_b = _make_source(db_session, user_b.id, vault)

        for src in (src_a, src_b):
            scan_and_ingest(db_session, src.id)
            for doc in db_session.query(KbDocument).filter(KbDocument.source_id == src.id).all():
                _embed(db_session, src.user_id, doc)

        emb_a = _embedding_count(db_session, user_a.id)
        emb_b = _embedding_count(db_session, user_b.id)
        assert emb_a > 0 and emb_b > 0

        # Dry run reports but deletes nothing.
        dry = purge_source(db_session, src_b.id, dry_run=True)
        assert dry["dry_run"] is True and dry["documents"] == 2
        assert db_session.get(KbSource, src_b.id) is not None

        # Real purge.
        report = purge_source(db_session, src_b.id)
        assert report["deleted"] is True
        assert db_session.get(KbSource, src_b.id) is None
        assert (
            db_session.query(KbDocument)
            .filter(KbDocument.source_id == src_b.id)
            .count()
            == 0
        )
        # B's embeddings gone; A's untouched.
        assert _embedding_count(db_session, user_b.id) == 0
        assert _embedding_count(db_session, user_a.id) == emb_a  # A kept all
        # The second purge attempt fails honestly.
        import pytest as _pytest

        with _pytest.raises(ValueError, match="not found"):
            purge_source(db_session, src_b.id)

    def test_purge_detaches_linked_courses(self, db_session, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        uid = _user(db_session).id
        src = _make_source(db_session, uid, vault)
        course = Course(
            user_id=uid, title="Cybersecurity", kb_source_id=src.id, kb_folder_path="cybersecurity"
        )
        db_session.add(course)
        db_session.commit()

        purge_source(db_session, src.id)
        db_session.refresh(course)
        assert course.kb_source_id is None


class TestOneFailedEmbedding:
    def test_failure_does_not_block_others_and_is_retryable(self, db_session, tmp_path, monkeypatch):
        uid = _user(db_session).id
        (tmp_path / "good.md").write_text("# Good\nsolid content " * 20)
        (tmp_path / "bad.md").write_text("# Bad\nfragile content " * 20)
        src = _make_source(db_session, uid, tmp_path)
        scan_and_ingest(db_session, src.id)
        good = _doc_by_path(db_session, src.id, "good.md")
        bad = _doc_by_path(db_session, src.id, "bad.md")

        from app.services import embeddings as _emb

        orig = _emb.backend_embed  # capture BEFORE the monkeypatch
        calls = {"n": 0}

        def flaky(texts, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:  # first document (bad) fails
                raise RuntimeError("embedding provider down")
            return orig(texts, **kwargs)

        monkeypatch.setattr("app.services.kb.embedder.embeddings.backend_embed", flaky)

        with pytest.raises(RuntimeError, match="embedding provider down"):
            _embed(db_session, uid, bad)  # fails once
        # Other documents keep working.
        _embed(db_session, uid, good)
        assert _embedding_count(db_session, uid) > 0

        monkeypatch.undo()  # restore the real backend
        retry = _embed(db_session, uid, bad)  # explicit retry succeeds
        assert retry["embedded"] >= 1
