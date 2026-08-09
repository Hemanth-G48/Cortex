"""Knowledge health analysis (Phase 3, Idea 27, phrases 61–70).

Pure, testable signal functions over ``kb_documents`` / ``kb_edges``:
- orphans — no incoming/outgoing edges and no MENTIONS (candidates for merge)
- dead links — WIKILINK/BACKLINK edges whose target document no longer exists
- stale notes — untouched for > ``KB_STALE_DAYS`` and never re-visited
- unindexed files — missing embeddings/chunks/tags (incomplete ingest)
- coverage gaps — subjects with few or no documents (stub for Idea 28)

``compute_health`` aggregates into a 0–100 weighted score per user.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    KbChunk,
    KbDocument,
    KbDocumentTag,
    KbEdge,
    KbEmbedding,
    KbTag,
)
from app.services.kb import utcnow

logger = logging.getLogger(__name__)

# Signals and their weight toward the 0–100 health score.
SIGNAL_WEIGHTS = {
    "orphans": 15.0,
    "dead_links": 15.0,
    "stale_notes": 20.0,
    "unindexed_files": 25.0,
    "coverage_gaps": 25.0,
    # Phase 4 (Idea 39, phrase 90): average note-quality across the vault.
    "avg_quality": 10.0,
}


def detect_orphans(db: Session, user_id: int) -> list[int]:
    """Documents with no edges and no tags (isolated notes)."""
    linked = set(
        row[0]
        for row in db.query(KbEdge.source_document_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id.isnot(None),
        )
        .all()
    )
    linked |= set(
        row[0]
        for row in db.query(KbEdge.target_document_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_document_id.isnot(None),
        )
        .all()
    )
    tagged = set(
        row[0]
        for row in db.query(KbDocumentTag.document_id)
        .filter(KbDocumentTag.user_id == user_id)
        .all()
    )
    docs = (
        db.query(KbDocument.id)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .all()
    )
    return [d for (d,) in docs if d not in linked and d not in tagged]


def detect_dead_links(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Edges whose target document no longer exists."""
    dead: list[dict[str, Any]] = []
    for edge in (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation.in_(["WIKILINK", "BACKLINK"]),
        )
        .all()
    ):
        target = edge.target_document_id
        if target is None:
            continue
        exists = (
            db.query(KbDocument.id)
            .filter(KbDocument.id == target, KbDocument.user_id == user_id)
            .first()
        )
        if exists is None:
            dead.append(
                {
                    "edge_id": edge.id,
                    "source_document_id": edge.source_document_id,
                    "target_document_id": target,
                    "relation": edge.relation,
                }
            )
    return dead


def detect_stale_notes(
    db: Session, user_id: int, stale_days: int | None = None
) -> list[int]:
    """Documents untouched for > ``KB_STALE_DAYS``."""
    stale_days = stale_days or settings.KB_STALE_DAYS
    cutoff = utcnow() - timedelta(days=stale_days)
    rows = (
        db.query(KbDocument.id)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
            func.coalesce(KbDocument.updated_at, KbDocument.created_at) < cutoff,
        )
        .all()
    )
    return [d for (d,) in rows]


def detect_unindexed_files(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Documents missing embeddings, chunks, or tags (incomplete ingest)."""
    issues: list[dict[str, Any]] = []
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .all()
    )
    chunk_counts = dict(
        db.query(KbChunk.document_id, func.count(KbChunk.id))
        .filter(KbChunk.user_id == user_id)
        .group_by(KbChunk.document_id)
        .all()
    )
    embed_counts = dict(
        db.query(KbEmbedding.chunk_id, func.count(KbEmbedding.id))
        .filter(KbEmbedding.user_id == user_id)
        .group_by(KbEmbedding.chunk_id)
        .all()
    )
    tag_counts = dict(
        db.query(KbDocumentTag.document_id, func.count(KbDocumentTag.id))
        .filter(KbDocumentTag.user_id == user_id)
        .group_by(KbDocumentTag.document_id)
        .all()
    )
    for doc in docs:
        problems = []
        if chunk_counts.get(doc.id, 0) == 0:
            problems.append("no_chunks")
        if embed_counts.get(doc.id, 0) == 0:
            problems.append("no_embeddings")
        if tag_counts.get(doc.id, 0) == 0:
            problems.append("no_tags")
        if problems:
            issues.append({"document_id": doc.id, "missing": problems})
    return issues


def average_quality(db: Session, user_id: int) -> float:
    """Mean cached ``quality_score`` across the user's documents (Idea 39).

    Returns 100.0 when no document has a score yet — an empty vault has no
    quality problems (mirrors the no-documents ⇒ score 100 rule).
    """
    rows = (
        db.query(KbDocument.quality_score)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
            KbDocument.quality_score.is_not(None),
        )
        .all()
    )
    scores = [r[0] for r in rows]
    if not scores:
        return 100.0
    return round(sum(scores) / len(scores), 1)


def coverage_gaps(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Topic→coverage stub (Idea 28, phrase 66).

    Phase 5 (Idea 38) feeds real subject topics; for now report documents with
    no tags at all as an implicit "untagged" coverage gap.
    """
    total = (
        db.query(KbDocument.id)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .count()
    )
    tagged = (
        db.query(KbDocumentTag.document_id)
        .filter(KbDocumentTag.user_id == user_id)
        .distinct()
        .count()
    )
    if total == 0:
        return [{"topic": "untagged", "covered": 0.0, "coverage": 0.0}]
    coverage = tagged / total
    return [{"topic": "untagged", "covered": tagged, "coverage": coverage}]


def compute_health(db: Session, user_id: int) -> dict[str, Any]:
    """Aggregate all signals into a 0–100 weighted score (phrase 67)."""
    orphans = detect_orphans(db, user_id)
    dead_links = detect_dead_links(db, user_id)
    stale = detect_stale_notes(db, user_id)
    unindexed = detect_unindexed_files(db, user_id)
    gaps = coverage_gaps(db, user_id)
    avg_q = average_quality(db, user_id)

    doc_count = (
        db.query(KbDocument.id)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .count()
    )
    edge_count = (
        db.query(KbEdge.id).filter(KbEdge.user_id == user_id).count()
    )

    # Each signal contributes a 0–1 "badness"; score = 100 − weighted badness.
    badness = {
        "orphans": (len(orphans) / doc_count) if doc_count else 0.0,
        "dead_links": min(1.0, len(dead_links) / max(1, edge_count)),
        "stale_notes": (len(stale) / doc_count) if doc_count else 0.0,
        "unindexed_files": (len(unindexed) / doc_count) if doc_count else 0.0,
        "coverage_gaps": gaps[0]["coverage"] if gaps else 1.0,
        "avg_quality": (100.0 - avg_q) / 100.0 if doc_count else 0.0,
    }
    penalty = sum(
        badness[key] * SIGNAL_WEIGHTS[key] for key in SIGNAL_WEIGHTS
    )
    score = max(0.0, min(100.0, 100.0 - penalty))

    return {
        "score": round(score, 1),
        "document_count": doc_count,
        "edge_count": edge_count,
        "signals": {
            "orphans": {"count": len(orphans), "document_ids": orphans},
            "dead_links": {"count": len(dead_links), "edges": dead_links},
            "stale_notes": {"count": len(stale), "document_ids": stale},
            "unindexed_files": {
                "count": len(unindexed),
                "documents": unindexed,
            },
            "coverage_gaps": gaps,
            "avg_quality": {"average": avg_q, "weight": SIGNAL_WEIGHTS["avg_quality"]},
        },
    }


__all__ = [
    "detect_orphans",
    "detect_dead_links",
    "detect_stale_notes",
    "detect_unindexed_files",
    "coverage_gaps",
    "average_quality",
    "compute_health",
]
