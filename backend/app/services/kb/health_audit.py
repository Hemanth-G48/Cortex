"""Vault Health Audit workflow — one dashboard over the existing health signals.

Aggregates (READ-ONLY, deterministic, no LLM calls on navigation):

- **missing notes** — ``suggestions.list_suggestions`` (Phase 8 Idea 77)
- **outdated notes** — ``outdated.review_queue`` (Phase 8 Idea 78)
- **near-duplicates** — ``neardup.list_duplicates`` (Phase 2 Idea 19)
- **low-quality docs** — ``quality.list_by_score`` (Phase 4 Idea 39)
- **dead links / stale / orphans** — ``health.compute_health`` (Phase 3 Ideas 27–28)

Explicit user actions (POST only):

- ``rescan`` — re-run the cheap detectors (outdated.scan + neardup scan is
  skipped here — it is embedding-heavy; the rescan only refreshes the
  read-mostly signals and the health score).
- ``dismiss_missing`` — permanent (phrase 67).
- ``resolve_outdated`` — updated | archived | dismissed (phrase 77).
- ``archive_duplicate`` — mark a duplicate document archived.

The audit never invents a signal: every section lists real rows already
computed by the underlying services.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.kb import health as health_svc
from app.services.kb import neardup as neardup_svc
from app.services.kb import outdated as outdated_svc
from app.services.kb import suggestions as suggestions_svc


def audit(db: Session, user_id: int, *, limit: int = 12) -> dict:
    """Read-only aggregate health snapshot (never mutates, never calls LLM).

    The low-quality section reads only the CACHED quality score — it never
    recomputes (``quality.get_or_compute`` writes on read), so a page load
    stays a pure read. ``rescan`` is the explicit action that recomputes.
    """
    missing = suggestions_svc.list_suggestions(db, user_id, status="suggested", limit=limit)
    outdated = outdated_svc.review_queue(db, user_id, status="open", limit=limit)
    duplicates = neardup_svc.list_duplicates(db, user_id)[:limit]
    quality = _cached_quality(db, user_id, limit)
    health = health_svc.compute_health(db, user_id)

    # Attach titles to duplicate pairs (the duplicate edge only has ids).
    dup_items = _with_titles(db, user_id, duplicates)

    return {
        "health": {
            "score": health.get("score"),
            "document_count": health.get("document_count"),
            "edge_count": health.get("edge_count"),
            "dead_links": health.get("signals", {}).get("dead_links", {}).get("count", 0),
            "orphans": health.get("signals", {}).get("orphans", {}).get("count", 0),
            "stale_notes": health.get("signals", {}).get("stale_notes", {}).get("count", 0),
            "unindexed_files": health.get("signals", {}).get("unindexed_files", {}).get("count", 0),
        },
        "sections": {
            "missing_notes": missing,
            "outdated_notes": outdated,
            "duplicates": dup_items,
            "low_quality": quality,
        },
        "counts": {
            "missing_notes": len(missing),
            "outdated_notes": len(outdated),
            "duplicates": len(dup_items),
            "low_quality": len(quality),
        },
        "scanned_at": None,
    }


def _cached_quality(db: Session, user_id: int, limit: int) -> list[dict]:
    """Low-scoring documents from the CACHED score only (pure read)."""
    from app.models import KbDocument

    rows = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
            KbDocument.quality_score.is_not(None),
        )
        .order_by(KbDocument.quality_score.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "document_id": d.id,
            "title": d.title or d.path_rel or f"doc {d.id}",
            "doc_type": d.doc_type,
            "score": d.quality_score,
            "components": {},
            "suggestions": 0,
        }
        for d in rows
    ]


def _with_titles(db: Session, user_id: int, duplicates: list[dict]) -> list[dict]:
    from app.models import KbDocument

    ids = set()
    for d in duplicates:
        ids.add(d["document_id"])
        ids.add(d["duplicate_of_id"])
    titles = {
        doc.id: doc.title or doc.path_rel or f"doc {doc.id}"
        for doc in db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.id.in_(ids))
        .all()
    }
    out = []
    for d in duplicates:
        out.append(
            {
                **d,
                "title": titles.get(d["document_id"]),
                "duplicate_of_title": titles.get(d["duplicate_of_id"]),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Explicit user actions (POST only)
# ---------------------------------------------------------------------------


def rescan(db: Session, user_id: int) -> dict:
    """Re-run the cheap detectors + health score (explicit user action).

    Refreshes outdated-note detection and the aggregate health score. Near-dup
    scanning is intentionally NOT run here — it is embedding-heavy and has its
    own explicit endpoint; the audit lists what is already recorded.
    """
    scan = outdated_svc.scan(db, user_id)
    health = health_svc.compute_health(db, user_id)
    db.commit()
    return {
        "ok": True,
        "created_outdated": scan.get("created", 0),
        "health_score": health.get("score"),
    }


def dismiss_missing(db: Session, user_id: int, suggestion_id: int) -> dict:
    try:
        return suggestions_svc.dismiss_suggestion(db, user_id, suggestion_id)
    except ValueError as e:
        raise ValueError(str(e))


def resolve_outdated(db: Session, user_id: int, note_id: int, action: str) -> dict:
    return outdated_svc.resolve(db, user_id, note_id, action)


def archive_duplicate(db: Session, user_id: int, document_id: int) -> dict:
    return neardup_svc.archive_document(db, user_id, document_id)
