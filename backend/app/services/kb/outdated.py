"""Phase 8 outdated-note detection (Idea 78).

Three detectors feed one review queue (``OutdatedNote`` rows, status
open → updated | archived | dismissed):

- ``stale`` — a document untouched/unread past ``KB_STALE_DAYS`` (Phase 3 health
  signal).
- ``material_changed`` — a document references another document (WIKILINK /
  BACKLINK / CITES / RELATED edge) whose content was re-indexed *after* the
  note was written, so the note may restate outdated material.
- ``contradiction`` — similar documents (sharing MENTIONS concepts) where an
  LLM verdict over the pair says ``contradicts``. Budget-capped
  (``KB_DAILY_GEN_LIMIT``); the deterministic fallback never *claims* a
  contradiction it cannot see — it only returns ``supports``/``unrelated``.

Every query is user-scoped; ``scan`` is idempotent (open/updated rows are never
re-created).
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbConcept, KbDocument, KbEdge, OutdatedNote
from app.services import ai_client
from app.services.kb import utcnow
from app.services.kb.budget import budget_allows, record_generation

logger = logging.getLogger(__name__)

REASONS = ("contradiction", "stale", "material_changed")
OPEN_STATUSES = ("open", "updated")
REFERENCE_RELATIONS = ("WIKILINK", "BACKLINK", "CITES", "RELATED", "SHARES_CONCEPT")

# Deterministic keyword fallback for the contradiction verdict (phrase 73).
CONTRADICTION_KEYWORDS = (
    "contradicts",
    "incorrectly",
    "is wrong",
    "differs from",
    "no longer",
    "revised",
)
SUPPORT_KEYWORDS = ("supports", "confirms", "consistent with", "aligns with")
# Hard ceiling on LLM-checked pairs per scan (cost guard).
MAX_PAIRS_PER_SCAN = 10


def _already_flagged(db: Session, user_id: int, document_id: int, reason: str) -> bool:
    return (
        db.query(OutdatedNote)
        .filter(
            OutdatedNote.user_id == user_id,
            OutdatedNote.document_id == document_id,
            OutdatedNote.reason == reason,
            OutdatedNote.status.in_(OPEN_STATUSES),
        )
        .first()
        is not None
    )


def _add(db: Session, user_id: int, document_id: int, reason: str, evidence: dict) -> dict | None:
    if reason not in REASONS or _already_flagged(db, user_id, document_id, reason):
        return None
    row = OutdatedNote(
        user_id=user_id,
        document_id=document_id,
        reason=reason,
        evidence_json=json.dumps(evidence, ensure_ascii=False, default=str),
    )
    db.add(row)
    db.flush()
    return {
        "id": row.id,
        "document_id": document_id,
        "reason": reason,
        "evidence": evidence,
    }


# --------------------------------------------------------------------------- #
# Detector 1 — stale
# --------------------------------------------------------------------------- #
def _stale_candidates(db: Session, user_id: int, stale_days: int) -> list[dict]:
    now = utcnow()
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
        )
        .all()
    )
    out: list[dict] = []
    for d in docs:
        last = d.updated_at or d.indexed_at or d.created_at or now
        age_days = max(0.0, (now - last).total_seconds() / 86400.0)
        if age_days >= stale_days:
            item = _add(
                db,
                user_id,
                d.id,
                "stale",
                {"last_activity": last.isoformat(), "stale_days": round(age_days, 1)},
            )
            if item:
                out.append(item)
    return out


# --------------------------------------------------------------------------- #
# Detector 2 — changed materials
# --------------------------------------------------------------------------- #
def _material_changed_candidates(db: Session, user_id: int) -> list[dict]:
    edges = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_document_id.is_not(None),
            KbEdge.relation.in_(REFERENCE_RELATIONS),
        )
        .all()
    )
    docs = {d.id: d for d in db.query(KbDocument).filter(KbDocument.user_id == user_id).all()}
    out: list[dict] = []
    for e in edges:
        src = docs.get(e.source_document_id)
        tgt = docs.get(e.target_document_id)
        if not src or not tgt:
            continue
        # The referenced material was re-indexed *after* the note was written.
        if tgt.status == "changed" and tgt.updated_at and src.updated_at and tgt.updated_at > src.updated_at:
            item = _add(
                db,
                user_id,
                src.id,
                "material_changed",
                {
                    "referenced_document_id": tgt.id,
                    "referenced_updated_at": tgt.updated_at.isoformat(),
                    "note_updated_at": src.updated_at.isoformat(),
                    "relation": e.relation,
                },
            )
            if item:
                out.append(item)
    return out


# --------------------------------------------------------------------------- #
# Detector 3 — contradiction (similar pairs + LLM verdict)
# --------------------------------------------------------------------------- #
def _shared_concept_pairs(db: Session, user_id: int, limit: int = MAX_PAIRS_PER_SCAN) -> list[tuple[KbDocument, KbDocument, list[str]]]:
    """Docs sharing a MENTIONS concept, paired newer-vs-older (phrase 72)."""
    edges = (
        db.query(KbEdge, KbConcept)
        .join(KbConcept, KbConcept.id == KbEdge.target_concept_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
        )
        .all()
    )
    by_concept: dict[int, list[tuple[int, str]]] = {}
    for e, c in edges:
        by_concept.setdefault(c.id, []).append((e.source_document_id, c.canonical_name))
    docs = {d.id: d for d in db.query(KbDocument).filter(KbDocument.user_id == user_id).all()}
    pairs: list[tuple[KbDocument, KbDocument, list[str]]] = []
    for concept_id, members in by_concept.items():
        if len(members) < 2:
            continue
        seen_doc_pairs: set[tuple[int, int]] = set()
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a_id, name = members[i]
                b_id, _ = members[j]
                if (a_id, b_id) in seen_doc_pairs or (b_id, a_id) in seen_doc_pairs:
                    continue
                seen_doc_pairs.add((a_id, b_id))
                da = docs.get(a_id)
                db_ = docs.get(b_id)
                if not da or not db_:
                    continue
                # Order: older first, newer second.
                old, new = sorted([da, db_], key=lambda d: (d.updated_at or d.created_at or utcnow()))
                pairs.append((old, new, [name]))
                if len(pairs) >= limit:
                    return pairs
    return pairs


def _keyword_verdict(old_text: str, new_text: str) -> str:
    t = (new_text or "").lower()
    if any(k in t for k in CONTRADICTION_KEYWORDS):
        return "contradicts"
    if any(k in t for k in SUPPORT_KEYWORDS):
        return "supports"
    return "unrelated"


def _excerpt(doc: KbDocument, limit: int = 600) -> str:
    return (doc.extracted_text or "").strip()[:limit]


def _contradiction_candidates(db: Session, user_id: int) -> list[dict]:
    pairs = _shared_concept_pairs(db, user_id)
    out: list[dict] = []
    for old, new, shared in pairs:
        verdict: str
        reason: str | None = None
        ai = ai_client.ai_available()
        if ai and budget_allows(db, user_id, 1):
            from app.services.prompts import contradiction_prompt

            parsed = ai_client.generate_json(
                contradiction_prompt(old.title or old.path_rel or f"doc {old.id}", _excerpt(old),
                                     new.title or new.path_rel or f"doc {new.id}", _excerpt(new)),
                max_tokens=300,
                temperature=0.2,
            )
            if isinstance(parsed, dict):
                verdict = str(parsed.get("verdict") or "unrelated").strip().lower()
                if verdict not in ("contradicts", "supports", "unrelated"):
                    verdict = "unrelated"
                reason = str(parsed.get("reason") or "") or None
                record_generation(db, user_id, "contradiction")
            else:
                verdict = _keyword_verdict(_excerpt(old), _excerpt(new))
        else:
            verdict = _keyword_verdict(_excerpt(old), _excerpt(new))

        if verdict != "contradicts":
            continue
        item = _add(
            db,
            user_id,
            new.id,
            "contradiction",
            {
                "other_document_id": old.id,
                "shared_concepts": shared,
                "verdict": verdict,
                "reason": reason,
            },
        )
        if item:
            out.append(item)
    return out


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def scan(db: Session, user_id: int) -> dict:
    """Run all three detectors; returns newly created candidates (phrase 77)."""
    stale = _stale_candidates(db, user_id, settings.KB_STALE_DAYS)
    changed = _material_changed_candidates(db, user_id)
    contrad = _contradiction_candidates(db, user_id)
    created = stale + changed + contrad
    if created:
        db.commit()
    return {
        "scanned": True,
        "created": len(created),
        "items": created,
    }


def review_queue(db: Session, user_id: int, *, status: str = "open", limit: int = 50) -> list[dict]:
    rows = (
        db.query(OutdatedNote, KbDocument)
        .join(KbDocument, KbDocument.id == OutdatedNote.document_id)
        .filter(OutdatedNote.user_id == user_id, OutdatedNote.status == status)
        .order_by(OutdatedNote.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": n.id,
            "document_id": n.document_id,
            "title": d.title or d.path_rel or f"doc {d.id}",
            "reason": n.reason,
            "evidence": json.loads(n.evidence_json) if n.evidence_json else None,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n, d in rows
    ]


def resolve(db: Session, user_id: int, note_id: int, action: str) -> dict:
    """Resolve a review item (updated | archived | dismissed) (phrase 77)."""
    row = (
        db.query(OutdatedNote)
        .filter(OutdatedNote.id == note_id, OutdatedNote.user_id == user_id)
        .first()
    )
    if row is None:
        raise ValueError("Outdated note not found")
    if action not in ("updated", "archived", "dismissed"):
        raise ValueError("action must be updated | archived | dismissed")
    row.status = action
    db.flush()
    return {"id": row.id, "document_id": row.document_id, "status": row.status}
