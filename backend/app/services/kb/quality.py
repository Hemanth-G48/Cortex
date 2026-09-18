"""Note-quality scoring (Phase 4, Idea 39).

A pure, testable composite 0–100 score per document over five components
(length, heading structure, link density, recency, concept coverage) with
configurable weights (``KB_QUALITY_WEIGHTS``). Scores are cached on the
``KbDocument`` row and recomputed on content change (phrase 84). Optional
LLM improvement suggestions are stored with a pending/dismissed lifecycle
(phrase 85).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbDocumentTag, KbEdge, KbQualitySuggestion
from app.services.ai_fallback import demo_quality_suggestions
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.summarize import document_content

logger = logging.getLogger(__name__)

COMPONENTS = ("length", "headings", "links", "recency", "coverage")


def _component_scores(db: Session, doc: KbDocument) -> dict[str, float]:
    """Raw 0–1 component scores (phrase 82)."""
    char_count = doc.char_count or 0
    length = min(1.0, char_count / 4000.0)

    outline = KbService.json_loads(doc.outline_json)
    headings = min(1.0, (len(outline) if outline else 0) / 5.0)

    link_count = (
        db.query(KbEdge.id)
        .filter(
            KbEdge.user_id == doc.user_id,
            KbEdge.source_document_id == doc.id,
        )
        .count()
    )
    links = min(1.0, link_count / 3.0)

    fresh_days = settings.KB_QUALITY_FRESH_DAYS
    ref = doc.updated_at or doc.created_at or utcnow()
    recency = 1.0 if ref >= utcnow() - timedelta(days=fresh_days) else 0.2

    concept_count = (
        db.query(KbEdge.id)
        .filter(
            KbEdge.user_id == doc.user_id,
            KbEdge.source_document_id == doc.id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
        )
        .count()
    )
    coverage = min(1.0, concept_count / 3.0)

    return {
        "length": round(length, 4),
        "headings": round(headings, 4),
        "links": round(links, 4),
        "recency": round(recency, 4),
        "coverage": round(coverage, 4),
    }


def compute_quality(db: Session, doc: KbDocument) -> dict:
    """Composite score with per-component detail (phrase 81)."""
    components = _component_scores(db, doc)
    weights = settings.kb_quality_weights
    score = sum(components[k] * weights.get(k, 0.0) for k in COMPONENTS)
    return {
        "score": round(score * 100),
        "components": components,
        "weights": weights,
        "computed_at": utcnow().isoformat(),
    }


def get_or_compute(db: Session, doc: KbDocument, force: bool = False) -> dict:
    """Return the cached quality result, recomputing on demand (phrase 84)."""
    if not force and doc.quality_score is not None:
        detail = KbService.json_loads(doc.quality_detail) or {}
        return {"score": doc.quality_score, **detail}

    result = compute_quality(db, doc)
    doc.quality_score = result["score"]
    doc.quality_detail = KbService.json_dumps(result)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return result


def recompute_for_document(db: Session, doc: KbDocument) -> int:
    """Ingest-stage recompute (content changed → cache is stale). Best-effort.

    Also self-registers as a post-ingest hook so pipeline.py doesn't hardcode
    this module.
    """
    register_hook_once()
    return _quality_hook(db, doc)


_hook_registered = False


def register_hook_once() -> None:
    """Self-register as a post-ingest hook (idempotent, best-effort)."""
    global _hook_registered
    if _hook_registered:
        return
    try:
        from app.services.kb.pipeline import register_post_ingest
        register_post_ingest("quality.recompute_for_document", _quality_hook)
        _hook_registered = True
    except Exception:  # noqa: BLE001
        pass


def _quality_hook(db: Session, doc: KbDocument) -> int:
    """Post-ingest hook: recompute quality score for the document."""
    try:
        result = compute_quality(db, doc)
        doc.quality_score = result["score"]
        doc.quality_detail = KbService.json_dumps(result)
        db.add(doc)
        db.commit()
        return result["score"]
    except Exception as exc:  # noqa: BLE001 — never break ingest
        logger.warning("Quality recompute failed for doc %s: %s", doc.id, exc)
        db.rollback()
        return doc.quality_score or 0


# ---------------------------------------------------------------------------
# Suggestions (phrase 85)
# ---------------------------------------------------------------------------

def generate_suggestions(db: Session, doc: KbDocument) -> list[dict]:
    """LLM (or heuristic) improvement suggestions stored status=pending."""
    from app.services.ai_client import ai_available

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, doc.user_id):
        return []

    link_count = (
        db.query(KbEdge.id)
        .filter(KbEdge.user_id == doc.user_id, KbEdge.source_document_id == doc.id)
        .count()
    )
    concept_count = (
        db.query(KbEdge.id)
        .filter(
            KbEdge.user_id == doc.user_id,
            KbEdge.source_document_id == doc.id,
            KbEdge.relation == "MENTIONS",
        )
        .count()
    )
    has_outline = bool(KbService.json_loads(doc.outline_json))
    content = document_content(db, doc)

    raw: list[dict] = []
    if not used_fallback:
        try:
            from app.services.ai_client import generate_json
            from app.services.prompts import quality_suggestions_prompt

            concept_names = [
                row[0]
                for row in db.execute(
                    "SELECT canonical_name FROM kb_concepts WHERE user_id = :uid LIMIT 12",
                    {"uid": doc.user_id},
                ).fetchall()
            ]
            parsed = generate_json(
                quality_suggestions_prompt(content, concept_names),
                max_tokens=800,
                temperature=0.4,
            )
            sugs = parsed.get("suggestions") if isinstance(parsed, dict) else parsed
            if isinstance(sugs, list):
                raw = [
                    {
                        "action": str(s.get("action") or "expand")[:100],
                        "detail": str(s.get("detail") or "")[:600],
                    }
                    for s in sugs
                    if isinstance(s, dict)
                ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Quality suggestions failed for doc %s: %s", doc.id, exc)
            raw = []

    if not raw:
        used_fallback = True
        raw = demo_quality_suggestions(content, link_count, has_outline, concept_count)

    if not used_fallback:
        record_generation(db, doc.user_id, "quality")

    saved: list[dict] = []
    for s in raw[:5]:
        row = KbQualitySuggestion(
            user_id=doc.user_id,
            document_id=doc.id,
            action=s["action"],
            detail=s.get("detail"),
            status="pending",
        )
        db.add(row)
        saved.append(row)
    db.commit()
    return [
        {"id": r.id, "action": r.action, "detail": r.detail, "status": r.status}
        for r in saved
    ]


def list_suggestions(db: Session, user_id: int, document_id: int) -> list[dict]:
    rows = (
        db.query(KbQualitySuggestion)
        .filter(
            KbQualitySuggestion.user_id == user_id,
            KbQualitySuggestion.document_id == document_id,
            KbQualitySuggestion.status == "pending",
        )
        .order_by(KbQualitySuggestion.id.desc())
        .all()
    )
    return [
        {"id": r.id, "action": r.action, "detail": r.detail, "status": r.status}
        for r in rows
    ]


def dismiss_suggestion(db: Session, user_id: int, suggestion_id: int) -> bool:
    row = (
        db.query(KbQualitySuggestion)
        .filter(
            KbQualitySuggestion.id == suggestion_id,
            KbQualitySuggestion.user_id == user_id,
        )
        .first()
    )
    if row is None:
        return False
    row.status = "dismissed"
    db.add(row)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Aggregate list (phrase 87)
# ---------------------------------------------------------------------------

def list_by_score(db: Session, user_id: int, sort: str = "score") -> dict:
    """Per-user quality work-list, lowest score first by default."""
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .all()
    )
    items = []
    for d in docs:
        result = get_or_compute(db, d)
        items.append(
            {
                "document_id": d.id,
                "title": d.title or d.path_rel or f"doc {d.id}",
                "doc_type": d.doc_type,
                "score": result["score"],
                "components": result.get("components", {}),
                "suggestions": len(list_suggestions(db, user_id, d.id)),
            }
        )
    reverse = str(sort) == "score" and False or str(sort) == "-score"
    items.sort(key=lambda i: (i["score"], i["document_id"]), reverse=reverse)
    return {"items": items, "total": len(items)}
