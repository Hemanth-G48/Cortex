"""Phase 9 automation registry + runner (Ideas 81–90).

The one unifying pattern for every Phase 9 idea:

    Batch job (runs on ``kb_jobs``, gated by a ``KB_AUTO_*`` toggle and capped
    by a per-run budget) → proposals (queued rows with provenance) → user
    review queue (batch approve/reject) → applied with version-history
    logging. Nothing auto-commits without review.

Feature modules register a job with the :func:`auto_job` decorator; this
module is the runner that discovers, gates, and dispatches them. Each job
function has the signature::

    def run(db: Session, user_id: int, limit: int | None = None) -> dict

returning a summary dict (``{"processed": n, ...}``). The runner persists a
``kb_jobs`` row per run so every automation is auditable like a scan/ingest.
"""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbJob
from app.services.kb import utcnow
from app.services.kb.jobs import get_executor, sync_mode

logger = logging.getLogger(__name__)

# Modules that register ``@auto_job`` handlers. Imported lazily so the
# foundation stays importable before every group lands; a missing module
# simply contributes no jobs (each is an opt-in toggle anyway).
FEATURE_MODULES = [
    # Idea 81 — auto-categorize new notes
    "app.services.kb.auto_categorize",
    # Idea 82 — scheduled auto-tag
    "app.services.kb.auto_tag",
    # Idea 83 — scheduled auto-link
    "app.services.kb.auto_link",
    # Idea 84 — scheduled duplicate detection
    "app.services.kb.auto_duplicates",
    # Idea 85 — auto-create flashcards from new notes
    "app.services.kb.auto_flashcards",
    # Idea 86 — scheduled summaries
    "app.services.kb.auto_summary",
    # Idea 87 — scheduled mind maps
    "app.services.kb.auto_mindmap",
    # Idea 88 — auto-update study plans
    "app.services.kb.auto_plan_sync",
    # Idea 89 — auto-sync external repositories
    "app.services.kb.auto_sync",
    # Idea 90 — auto-create revision tasks
    "app.services.kb.auto_revision",
]


@dataclass
class AutoJob:
    """One registered Phase 9 automation job."""

    name: str
    toggle: str  # settings attr, e.g. "KB_AUTO_TAG_ENABLED" — default OFF
    fn: Callable  # fn(db, user_id, limit=None) -> dict
    cap: str = ""  # settings attr, e.g. "KB_AUTO_TAG_PER_NIGHT"; "" = no cap
    description: str = ""
    # Set to "summary"/"flashcards"/… when the job spends real LLM generations
    # — the runner then checks KB_DAILY_GEN_LIMIT before dispatching.
    budget_kind: str | None = None


# name -> AutoJob
JOBS: dict[str, AutoJob] = {}


def auto_job(
    name: str,
    *,
    toggle: str,
    cap: str,
    description: str = "",
    budget_kind: str | None = None,
) -> Callable[[Callable], Callable]:
    """Register a Phase 9 automation job under ``name``.

    ``toggle`` and ``cap`` name ``settings`` attributes; the job only runs when
    its toggle is True and the cap bounds per-run work. ``budget_kind`` (an
    entry in ``GEN_KINDS``) opts the job into the shared daily budget.
    """

    def decorator(fn: Callable) -> Callable:
        JOBS[name] = AutoJob(
            name=name,
            toggle=toggle,
            cap=cap or "",
            fn=fn,
            description=description,
            budget_kind=budget_kind,
        )
        return fn

    return decorator


def _load_features() -> None:
    """Import Phase 9 feature modules so their ``@auto_job`` registrations run."""
    for mod in FEATURE_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001 — module not built yet
            logger.debug("automation module %s not loaded: %s", mod, exc)


def registered_jobs() -> list[dict]:
    """List registered jobs with their gate/cap state (for the UI)."""
    _load_features()
    jobs = []
    for spec in JOBS.values():
        jobs.append(
            {
                "name": spec.name,
                "enabled": bool(getattr(settings, spec.toggle, False)),
                "toggle": spec.toggle,
                "cap": getattr(settings, spec.cap, None),
                "budget_kind": spec.budget_kind,
                "description": spec.description,
            }
        )
    return sorted(jobs, key=lambda j: j["name"])


def _execute(db: Session, job: KbJob, spec: AutoJob, limit: int | None = None) -> dict:
    """Run one job inline, mutating ``job`` in the caller's session."""
    job.status = "running"
    db.add(job)
    db.commit()
    try:
        summary = spec.fn(db, job.user_id, limit=limit) or {}
        job.status = "done"
        job.summary_json = json.dumps(summary)
        job.total_items = int(summary.get("processed", 0))
        job.processed_items = job.total_items
    except Exception as exc:  # noqa: BLE001 — capture, never crash the worker
        logger.exception("Automation job %s failed", job.name)
        job.status = "failed"
        job.error = str(exc)[:2000]
    job.finished_at = utcnow()
    db.add(job)
    db.commit()
    return job.status, job.summary_json


def run_one(
    db: Session,
    user_id: int,
    name: str,
    *,
    force: bool = False,
    limit: int | None = None,
) -> dict:
    """Run one automation job (respecting its toggle unless ``force``).

    Persists a ``kb_jobs`` row and dispatches synchronously in hermetic mode
    or on the shared executor otherwise — mirroring scan/ingest jobs.
    """
    _load_features()
    spec = JOBS.get(name)
    if spec is None:
        raise ValueError(f"unknown automation job: {name!r}")
    if not force and not getattr(settings, spec.toggle, False):
        return {
            "job": name,
            "skipped": True,
            "reason": f"{spec.toggle} is disabled (default off)",
        }
    if limit is None:
        limit = getattr(settings, spec.cap, None)

    job = KbJob(
        user_id=user_id,
        job_type="auto",
        status="queued",
        ref_type=name,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    def _worker(job_id: int) -> None:
        from app.database import SessionLocal

        _db = SessionLocal()
        try:
            _job = _db.query(KbJob).filter(KbJob.id == job_id).first()
            if _job is not None:
                _execute(_db, _job, spec, limit=limit)
        finally:
            _db.close()

    if sync_mode():
        _execute(db, job, spec, limit=limit)
    else:
        get_executor().submit(_worker, job.id)

    return {"job": name, "job_id": job.id, "status": job.status}


def run_all(db: Session, user_id: int, *, force: bool = False) -> dict:
    """Run every enabled automation job once, in registry order."""
    _load_features()
    results = []
    for name in sorted(JOBS):
        spec = JOBS[name]
        if not force and not getattr(settings, spec.toggle, False):
            results.append({"job": name, "skipped": True, "reason": "disabled"})
            continue
        results.append(run_one(db, user_id, name, force=force))
    return {"results": results, "count": len(results)}
