"""Idea 87 — auto-generate mind maps, scheduled (Phase 9 Automation).

The batch job runs the Phase 4 Idea 38 ``mindmap`` pipeline over qualifying
documents and caches the built tree in ``metadata_json`` (key ``mindmap_tree``)
so the document viewer renders it instantly (phrase 63).

Qualification (phrase 62): only documents whose ``outline_json`` has at least
``KB_AUTO_MINDMAP_MIN_HEADINGS`` headings are eligible — no outline, no map.

No LLM is spent (phrase 66): trees derive from the outline + concept mentions,
so ``budget_kind`` is intentionally unset and the job is CPU/IO-bound.
Idempotent (phrase 64/67): the cached tree records the document's content
hash; unchanged docs are skipped, and re-runs are cheap no-ops.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument
from app.services.kb import KbService
from app.services.kb.automation import auto_job
from app.services.kb.mindmap import build_tree

logger = logging.getLogger(__name__)

# metadata_json key where the cached tree + hash live.
MINDMAP_CACHE_KEY = "mindmap_tree"


def _outline_count(doc: KbDocument) -> int:
    outline = KbService.json_loads(doc.outline_json) or []
    return len(outline)


def _qualifying_docs(
    db: Session, user_id: int, min_headings: int
) -> list[KbDocument]:
    """Documents with enough heading structure to make a useful map (62)."""
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
            KbDocument.doc_type == "md",
            KbDocument.outline_json.is_not(None),
        )
        .order_by(KbDocument.id.asc())
        .all()
    )
    return [d for d in docs if _outline_count(d) >= min_headings]


@auto_job(
    "auto_mindmap",
    toggle="KB_AUTO_MINDMAP_ENABLED",
    cap="",  # outline-derived: no per-run cap needed, no budget spend
    description=(
        "Pre-generate and cache mind-map trees for structured documents (no "
        "AI cost)."
    ),
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Build + cache mind-map trees for qualifying documents (phrase 61)."""
    min_headings = settings.KB_AUTO_MINDMAP_MIN_HEADINGS
    docs = _qualifying_docs(db, user_id, min_headings)
    if limit is not None:
        docs = docs[:limit]

    cached = 0
    built = 0
    skipped = 0
    for doc in docs:
        metadata = KbService.json_loads(doc.metadata_json) or {}
        tree_cache = metadata.get(MINDMAP_CACHE_KEY) or {}
        if (
            tree_cache.get("content_hash")
            and tree_cache.get("content_hash") == doc.content_hash
            and tree_cache.get("tree")
        ):
            cached += 1
            continue  # unchanged doc → cheap no-op (phrase 64)
        try:
            tree = build_tree(db, user_id, doc)
        except Exception as exc:  # noqa: BLE001 — one bad doc never stops the job
            logger.warning("auto_mindmap failed for doc %s: %s", doc.id, exc)
            db.rollback()
            skipped += 1
            continue
        metadata[MINDMAP_CACHE_KEY] = {
            "content_hash": doc.content_hash,
            "tree": tree,
        }
        doc.metadata_json = KbService.json_dumps(metadata)
        db.add(doc)
        built += 1

    db.commit()
    return {
        "processed": len(docs),
        "built": built,
        "cached": cached,
        "skipped": skipped,
        "min_headings": min_headings,
    }
