"""Ingestion job queue & status (Idea 10).

An in-process ``ThreadPoolExecutor`` (max 2 workers) wraps scan/ingest work.
Jobs get their own DB session per batch — never the request's ``get_db``
session (phrase 97). In hermetic/small runs (AI disabled or under pytest)
jobs execute synchronously so tests stay deterministic (phrase 98).
"""

from __future__ import annotations

import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import KbDocument, KbJob, KbSource
from app.services.kb import utcnow
from app.services.kb.pipeline import ingest_document
from app.services.kb.scanner import scan_and_ingest

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kb-jobs")
    return _executor


def sync_mode() -> bool:
    """True when jobs should run inline (hermetic CI / tiny vaults)."""
    return (not settings.AI_ENABLED) or ("pytest" in sys.modules)


def _merge_summary(job: KbJob, summary: dict) -> None:
    """Write the job's summary_json, merging caller-set metadata (e.g.
    backfill's ``marked_dirty``) instead of clobbering it.

    Reloads the row so metadata committed by the submitting request (which
    may have happened after this worker loaded the job) is preserved.
    """
    db = Session.object_session(job)
    if db is not None:
        db.refresh(job)
    prev: dict = json.loads(job.summary_json) if job.summary_json else {}
    prev.update(summary)
    job.summary_json = json.dumps(prev)


def _run_inline(db: Session, job_id: int) -> None:
    """Execute a queued job using the provided session (caller owns the close)."""
    job = db.query(KbJob).filter(KbJob.id == job_id).first()
    # ``queued`` jobs run normally; ``interrupted`` jobs are re-dispatched by
    # resume_interrupted_jobs() at startup so a killed worker's work resumes.
    # Any other status (done/failed) is never re-executed.
    if job is None or job.status not in ("queued", "interrupted"):
        return  # idempotent — only queued/interrupted jobs execute
    job.status = "running"
    db.add(job)
    db.commit()
    try:
        if job.job_type == "reindex":
            # Phase 2 (Idea 20, phrase 96): reindex runs the dirty-flag
            # coordinator instead of a plain Phase 1 ingest.
            from app.services.kb import reindex as reindex_service

            if job.ref_type == "source":
                summary = reindex_service.reindex_documents(
                    db, job.user_id, source_id=job.ref_id
                )
                job.total_items = int(summary.get("documents", 0))
                job.processed_items = job.total_items
                _merge_summary(job, summary)
            else:
                ids = json.loads(job.ref_ids_json or "[]")
                job.total_items = len(ids)
                failures = 0
                # Phase 1 — batch-embed every pending chunk across the job's
                # documents in one pass so the local fastembed (GPU) model sees
                # large batches instead of a 1-4 chunk call per document.
                # This clears the embedding_dirty flags, so the per-doc loop
                # below only does the LLM/CPU stages (tags, concepts, edges).
                try:
                    batch_res = reindex_service.embed_dirty_batch(db, job.user_id, ids)
                    logger.info(
                        "Job %s batch-embedded %s chunks across %s docs (%s batches)",
                        job.id,
                        batch_res.get("embedded"),
                        batch_res.get("docs"),
                        batch_res.get("batches"),
                    )
                except Exception:  # noqa: BLE001 — never kill the job on embed-phase error
                    logger.exception("Batch embed phase failed for job %s", job.id)
                    db.rollback()
                for i, doc_id in enumerate(ids, start=1):
                    doc = (
                        db.query(KbDocument)
                        .filter(
                            KbDocument.id == doc_id,
                            KbDocument.user_id == job.user_id,
                        )
                        .first()
                    )
                    if doc is not None:
                        # Per-document stages only (embed → tags → concepts →
                        # edges) so processed_items advances at a steady rate.
                        # The whole-user passes (shared concepts, near-dup
                        # scan, index sync) run once after the loop — running
                        # them per document would make a large vault job
                        # quadratically slow.
                        stage = reindex_service.run_document_stages(db, doc)
                        if not stage.get("ok"):
                            failures += 1
                    job.processed_items = i
                    db.add(job)
                    db.commit()
                # Whole-user passes exactly once per job (phrases 89, 95).
                # ``reindex_documents`` with an empty id list runs no per-doc
                # stages — only the shared-concept, near-dup and index-sync
                # passes.
                summary = reindex_service.reindex_documents(
                    db,
                    job.user_id,
                    doc_ids=[],
                    include_neardup=True,
                    include_shared_concepts=True,
                )
                summary["failures"] = failures
                _merge_summary(job, summary)
        elif job.ref_type == "source":
            # A folder-scoped scan carries its relative subpath in
            # ``ref_ids_json`` (``["cybersecurity"]``); a whole-source scan
            # leaves it empty.
            subpath = None
            if job.ref_ids_json:
                try:
                    stored = json.loads(job.ref_ids_json)
                    if stored and isinstance(stored[0], str):
                        subpath = stored[0]
                except (ValueError, TypeError, IndexError):
                    subpath = None
            summary = scan_and_ingest(db, job.ref_id or 0, subpath=subpath)
            job.total_items = int(summary.get("files_seen", 0))
            job.processed_items = job.total_items
            job.summary_json = json.dumps(summary)
        else:
            ids = json.loads(job.ref_ids_json or "[]")
            job.total_items = len(ids)
            for i, doc_id in enumerate(ids, start=1):
                doc = (
                    db.query(KbDocument)
                    .filter(KbDocument.id == doc_id, KbDocument.user_id == job.user_id)
                    .first()
                )
                if doc is not None:
                    ingest_document(db, doc)
                job.processed_items = i
                db.add(job)
                db.commit()
        job.status = "done"
        # Event hook: after a scan/reindex completes, refresh KB-derived courses
        # so new vault material tagged `course:*` surfaces without a manual sync.
        if job.job_type in ("scan", "reindex", "ingest"):
            try:
                from app.services.course_derivation import derive_courses_from_tags

                derive_courses_from_tags(db, job.user_id)
            except Exception:  # noqa: BLE001 — never fail the job over course sync
                logger.exception(
                    "Course derivation after job %s failed", job.id
                )
    except Exception as exc:  # noqa: BLE001 — capture, never crash the worker
        logger.exception("Job %s failed", job.id)
        job.status = "failed"
        job.error = str(exc)[:2000]
    job.finished_at = utcnow()
    db.add(job)
    db.commit()


def run_job(session_factory: Callable[[], Session], job_id: int) -> None:
    """Worker body: load the job in a fresh session and execute it."""
    db = session_factory()
    try:
        _run_inline(db, job_id)
    except Exception:  # noqa: BLE001
        logger.exception("Job %s crashed before execution", job_id)
    finally:
        db.close()


def _dispatch(
    job: KbJob,
    session_factory: Callable[[], Session] | None = None,
    db: Session | None = None,
) -> None:
    """Run synchronously (hermetic) or enqueue on the executor.

    In sync mode with a request session passed, the job runs inline in the
    caller's session (phrase 98) — tests stay hermetic and never touch the
    app's SQLite file.
    """
    if sync_mode():
        if db is not None:
            _run_inline(db, job.id)
        else:
            run_job(session_factory or SessionLocal, job.id)
    else:
        get_executor().submit(run_job, session_factory or SessionLocal, job.id)


def submit_scan_job(
    db: Session,
    source_id: int,
    subpath: str | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> KbJob:
    """Enqueue a scan job (and return the KbJob row, phrase 92).

    ``subpath`` optionally scopes the scan to one folder inside the source
    root (relative path, already validated by the caller); it is carried on
    the job in ``ref_ids_json`` so the worker can replay it.
    """
    source = db.query(KbSource).filter(KbSource.id == source_id).first()
    if source is None:
        raise ValueError("source not found")
    job = KbJob(
        user_id=source.user_id,
        job_type="scan",
        status="queued",
        ref_type="source",
        ref_id=source_id,
    )
    if subpath:
        job.ref_ids_json = json.dumps([subpath])
    db.add(job)
    db.commit()
    db.refresh(job)
    _dispatch(job, session_factory, db=db)
    return job


def submit_ingest_job(
    db: Session,
    user_id: int,
    document_ids: list[int],
    session_factory: Callable[[], Session] | None = None,
    job_type: str = "ingest",
) -> KbJob:
    """Enqueue an ingest/reindex job for the given documents."""
    job = KbJob(
        user_id=user_id,
        job_type=job_type,
        status="queued",
        ref_type="documents",
        ref_ids_json=json.dumps(list(document_ids)),
        total_items=len(document_ids),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _dispatch(job, session_factory, db=db)
    return job


def submit_reindex_job(
    db: Session,
    user_id: int,
    source_id: int | None = None,
    document_ids: list[int] | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> KbJob:
    """Enqueue a Phase 2 reindex job (phrase 96).

    Scoped to ``source_id`` when given, otherwise to ``document_ids``.
    Runs through the same job queue with progress + resume semantics.
    """
    if source_id is not None:
        job = KbJob(
            user_id=user_id,
            job_type="reindex",
            status="queued",
            ref_type="source",
            ref_id=source_id,
        )
    else:
        job = KbJob(
            user_id=user_id,
            job_type="reindex",
            status="queued",
            ref_type="documents",
            ref_ids_json=json.dumps(list(document_ids or [])),
            total_items=len(document_ids or []),
        )
    db.add(job)
    db.commit()
    db.refresh(job)
    _dispatch(job, session_factory, db=db)
    return job


def resume_interrupted_jobs(
    session_factory: Callable[[], Session] | None = None,
) -> int:
    """Startup recovery (phrase 95): flip stuck ``running`` → ``interrupted``,
    then re-dispatch queued + interrupted jobs so work resumes."""
    sf = session_factory or SessionLocal
    db = sf()
    recovered = 0
    try:
        stuck = db.query(KbJob).filter(KbJob.status == "running").all()
        for job in stuck:
            job.status = "interrupted"
            db.add(job)
            recovered += 1
        db.commit()

        pending = (
            db.query(KbJob)
            .filter(KbJob.status.in_(["queued", "interrupted"]))
            .all()
        )
        for job in pending:
            _dispatch(job, sf)
        return recovered
    finally:
        db.close()
