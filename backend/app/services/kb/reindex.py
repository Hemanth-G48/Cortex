"""Incremental re-index coordinator (Second Brain Phase 2, Idea 20, phrases 91-98).

Drives the dirty-flag lifecycle on ``KbDocument`` (``embedding_dirty``,
``tags_dirty``, ``graph_dirty``) so re-indexing is incremental, idempotent
and resumable:

- Only *dirty* documents are processed (phrase 93).
- Stages run in dependency order (phrase 95): embeddings → auto-tags →
  concepts → graph edges → near-dup scan.
- Each stage clears its own flag only after it succeeds (phrase 93); a failed
  stage leaves the flag set so the next run resumes where it left off.
- A re-run after success is a no-op (idempotent, phrase 93/98).
- The whole run may be dispatched as a ``KbJob`` (``job_type=reindex``) via
  the job queue (phrase 96) or executed directly by the CLI (phrase 91).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import KbDocument
from app.services.kb import utcnow
from app.services.kb import graph
from app.services.kb.embedder import (
    embed_dirty_batch,
    embed_document_chunks,
    sync_index,
)
from app.services.kb.tagger import auto_tag_document
from app.services.kb.concepts import extract_for_document

logger = logging.getLogger(__name__)

# Stage order (phrase 95).
STAGE_ORDER = ("embedding", "tags", "concepts", "graph", "neardup")

# Dirty flag for each stage (a stage clears only its own flag).
STAGE_FLAG = {
    "embedding": "embedding_dirty",
    "tags": "tags_dirty",
    "concepts": "graph_dirty",
    "graph": "graph_dirty",
    "neardup": None,  # near-dup is a whole-user pass, not a per-doc flag
}


def mark_dirty(
    db: Session,
    user_id: int,
    source_id: int | None = None,
    flags: tuple[str, ...] = ("embedding_dirty", "tags_dirty", "graph_dirty"),
) -> int:
    """Set the given dirty flags on all (optionally source-scoped) documents.

    Used by ``backfill`` (phrase 92) — forces a full reindex of everything.
    Returns the number of documents marked.
    """
    query = db.query(KbDocument).filter(KbDocument.user_id == user_id)
    if source_id is not None:
        query = query.filter(KbDocument.source_id == source_id)
    docs = query.all()
    for doc in docs:
        for flag in flags:
            setattr(doc, flag, True)
        doc.updated_at = utcnow()
        db.add(doc)
    db.commit()
    return len(docs)


def dirty_documents(
    db: Session, user_id: int, source_id: int | None = None
) -> list[KbDocument]:
    """Documents with any Phase 2 dirty flag set (phrase 93)."""
    from sqlalchemy import or_

    query = db.query(KbDocument).filter(KbDocument.user_id == user_id)
    if source_id is not None:
        query = query.filter(KbDocument.source_id == source_id)
    return (
        query.filter(
            or_(
                KbDocument.embedding_dirty == True,  # noqa: E712
                KbDocument.tags_dirty == True,  # noqa: E712
                KbDocument.graph_dirty == True,  # noqa: E712
            )
        )
        .order_by(KbDocument.id.asc())
        .all()
    )


def run_document_stages(db: Session, doc: KbDocument) -> dict:
    """Run the dirty stages for a single document (phrase 95).

    Clears each flag only after its stage succeeds.  Never raises for
    content errors — a failing stage logs and leaves the flag set.
    """
    user_id = doc.user_id
    summary: dict = {"document_id": doc.id, "title": doc.title or doc.path_rel or ""}
    changed = False

    try:
        if doc.embedding_dirty:
            res = embed_document_chunks(db, user_id, doc.id)
            summary["embedded"] = res.get("embedded", 0)
            summary["skipped"] = res.get("skipped", 0)
            changed = True

        if doc.tags_dirty:
            auto_tag_document(db, doc)
            summary["tags"] = "ok"
            changed = True

        if doc.graph_dirty:
            # Concepts + MENTIONS edges (extract_for_document clears graph_dirty).
            count = extract_for_document(db, doc)
            summary["concepts"] = count
            # Wikilink/backlink edges (provenance=rule) + mentions from concepts.
            graph.build_wikilink_edges(db, user_id, doc, backlinks=True)
            graph.link_mentions_edges(db, user_id, doc)
            db.commit()
            changed = True

        summary["ok"] = True
    except Exception as exc:  # noqa: BLE001 — a failing stage must not kill the job
        logger.exception("Reindex stage failed for document %s", doc.id)
        summary["ok"] = False
        summary["error"] = str(exc)[:500]
        db.rollback()
    return summary


def reindex_documents(
    db: Session,
    user_id: int,
    source_id: int | None = None,
    doc_ids: list[int] | None = None,
    include_neardup: bool = True,
    include_shared_concepts: bool = True,
) -> dict:
    """Process dirty documents in stage order (phrase 93-95).

    Returns a summary dict: ``{documents, embedded, skipped, tags, concepts,
    edges, neardup_pairs, synced_vectors, dirty_remaining}``.
    """
    docs = dirty_documents(db, user_id, source_id=source_id)
    if doc_ids is not None:
        wanted = set(doc_ids)
        docs = [d for d in docs if d.id in wanted]

    summary: dict = {
        "documents": len(docs),
        "embedded": 0,
        "skipped": 0,
        "tags": 0,
        "concepts": 0,
        "edges": 0,
        "neardup_pairs": 0,
        "synced_vectors": 0,
        "dirty_remaining": 0,
        "source_id": source_id,
    }

    for doc in docs:
        stage = run_document_stages(db, doc)
        if stage.get("ok"):
            summary["embedded"] += stage.get("embedded", 0)
            summary["skipped"] += stage.get("skipped", 0)
            summary["tags"] += 1 if stage.get("tags") == "ok" else 0
            summary["concepts"] += stage.get("concepts", 0)
        else:
            logger.warning(
                "Reindex failed for doc %s: %s", doc.id, stage.get("error")
            )
            db.rollback()

    # Whole-user passes after per-doc stages (phrases 95, 89).
    if include_shared_concepts:
        try:
            from app.services.kb.related import infer_shared_concepts

            summary["edges"] += infer_shared_concepts(db, user_id)
        except Exception:  # noqa: BLE001
            logger.exception("Shared-concept inference failed during reindex")

    if include_neardup:
        try:
            from app.services.kb.neardup import scan_duplicates

            pairs = scan_duplicates(db, user_id)
            summary["neardup_pairs"] = len(pairs)
        except Exception:  # noqa: BLE001
            logger.exception("Near-dup scan failed during reindex")

    # Rebuild the in-memory/file index from kb_embeddings (phrase 15/18).
    try:
        synced = sync_index(db, user_id)
        summary["synced_vectors"] = synced.get("vectors", 0)
    except Exception:  # noqa: BLE001
        logger.exception("Index sync failed during reindex")

    summary["dirty_remaining"] = len(
        dirty_documents(db, user_id, source_id=source_id)
    )
    return summary


def backfill(
    db: Session,
    user_id: int,
    source_id: int | None = None,
    include_neardup: bool = True,
) -> dict:
    """Mark every document dirty, then run a full reindex (phrase 92/99)."""
    marked = mark_dirty(db, user_id, source_id=source_id)
    result = reindex_documents(
        db, user_id, source_id=source_id, include_neardup=include_neardup
    )
    result["marked_dirty"] = marked
    return result
