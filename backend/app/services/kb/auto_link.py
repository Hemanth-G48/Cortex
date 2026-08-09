"""Idea 83 — scheduled auto-link of related notes (Phase 9 Automation).

Runs an incremental embedding-similarity pass over the user's documents.
Pairs above ``KB_AUTO_LINK_CONFIDENCE`` become ``RELATED`` edges immediately
(status ``active``, provenance ``auto``); pairs between ``KB_SIM_THRESHOLD``
and the confidence bar are queued as *pending* edges for the review queue.
Rejected pairs are kept (status ``rejected``) and never re-proposed; accepted
pairs flip to ``active`` and join the graph like any manual edge.

No LLM is spent — embeddings already exist from Phase 2 indexing.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbEdge
from app.services.kb.automation import auto_job
from app.services.kb.related import _cosine, doc_avg_embedding

logger = logging.getLogger(__name__)


def _pair_key(a: int, b: int) -> frozenset[int]:
    """Undirected pair key — A↔B proposals are deduped regardless of direction."""
    return frozenset((a, b))


def _existing_pairs(
    db: Session, user_id: int, *statuses: str
) -> set[frozenset[int]]:
    rows = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_document_id.is_not(None),
            KbEdge.status.in_(statuses),
        )
        .all()
    )
    return {
        _pair_key(e.source_document_id, e.target_document_id) for e in rows
    }


def _upsert_edge(
    db: Session,
    user_id: int,
    a: int,
    b: int,
    score: float,
    status: str,
) -> None:
    """Create-or-refresh a RELATED edge between docs ``a`` and ``b``."""
    existing = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == a,
            KbEdge.target_document_id == b,
            KbEdge.relation == "RELATED",
        )
        .first()
    )
    if existing is None:
        existing = (
            db.query(KbEdge)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.source_document_id == b,
                KbEdge.target_document_id == a,
                KbEdge.relation == "RELATED",
            )
            .first()
        )
    if existing is not None:
        existing.weight = round(score, 4)
        existing.status = status
        existing.provenance = "auto"
        db.add(existing)
        return
    db.add(
        KbEdge(
            user_id=user_id,
            source_document_id=a,
            target_document_id=b,
            relation="RELATED",
            weight=round(score, 4),
            provenance="auto",
            target_type="document",
            status=status,
        )
    )


@auto_job(
    "auto_link",
    toggle="KB_AUTO_LINK_ENABLED",
    cap="KB_AUTO_LINK_PER_RUN",
    description=(
        "Create RELATED edges between similar notes; queue borderline pairs "
        "for review."
    ),
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Incremental similarity pass: auto-link + queue pending proposals."""
    if limit is None:
        limit = settings.KB_AUTO_LINK_PER_RUN

    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
        )
        .all()
    )
    vecs: dict[int, list[float]] = {}
    for doc in docs:
        vec = doc_avg_embedding(db, user_id, doc.id)
        if vec:
            vecs[doc.id] = vec
    if not vecs:
        return {"processed": 0, "linked": 0, "proposed": 0}

    active = _existing_pairs(db, user_id, "active")
    settled = active | _existing_pairs(db, user_id, "pending", "rejected")

    doc_ids = list(vecs.keys())
    threshold = settings.KB_SIM_THRESHOLD
    confidence = settings.KB_AUTO_LINK_CONFIDENCE

    linked = 0
    proposed = 0
    scanned = 0
    for i in range(len(doc_ids)):
        if linked + proposed >= limit:
            break
        a = doc_ids[i]
        va = vecs[a]
        for b in doc_ids[i + 1 :]:
            if linked + proposed >= limit:
                break
            key = _pair_key(a, b)
            if key in settled:
                continue
            score = _cosine(va, vecs[b])
            if score < threshold:
                continue
            scanned += 1
            if score >= confidence:
                _upsert_edge(db, user_id, a, b, score, "active")
                active.add(key)
                settled.add(key)
                linked += 1
            else:
                _upsert_edge(db, user_id, a, b, score, "pending")
                settled.add(key)
                proposed += 1
    db.commit()
    return {"processed": scanned, "linked": linked, "proposed": proposed}


def _serialize(e: KbEdge) -> dict:
    return {
        "edge_id": e.id,
        "source_document_id": e.source_document_id,
        "target_document_id": e.target_document_id,
        "relation": e.relation,
        "weight": e.weight,
        "provenance": e.provenance,
        "status": e.status,
    }


def queue(db: Session, user_id: int, limit: int = 200) -> list[dict]:
    """Pending auto-link proposals, strongest first."""
    rows = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.status == "pending",
            KbEdge.target_document_id.is_not(None),
        )
        .order_by(KbEdge.weight.desc())
        .limit(limit)
        .all()
    )
    return [_serialize(e) for e in rows]


def accept(db: Session, user_id: int, edge_ids: list[int]) -> int:
    """Promote approved pending edges to the live graph."""
    accepted = 0
    for eid in edge_ids:
        e = (
            db.query(KbEdge)
            .filter(
                KbEdge.id == eid,
                KbEdge.user_id == user_id,
                KbEdge.status == "pending",
            )
            .first()
        )
        if e is not None:
            e.status = "active"
            accepted += 1
    db.commit()
    return accepted


def reject(db: Session, user_id: int, edge_ids: list[int]) -> int:
    """Reject proposals — kept as ``rejected`` so they never re-propose."""
    rejected = 0
    for eid in edge_ids:
        e = (
            db.query(KbEdge)
            .filter(
                KbEdge.id == eid,
                KbEdge.user_id == user_id,
                KbEdge.status == "pending",
            )
            .first()
        )
        if e is not None:
            e.status = "rejected"
            rejected += 1
    db.commit()
    return rejected
