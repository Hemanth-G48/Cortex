"""Idea 81 — auto-categorize new notes into folders (Phase 9 Automation).

The nightly job scans for a deterministic category signal (frontmatter
``category`` / ``folder``) and queues a ``CategorizeSuggestion`` per move.
Nothing moves on its own: the user reviews the queue and batch-accepts, which
applies the ``path_rel`` change and logs the move in version history.

``budget_kind`` is unset — the proposal is rule-based and costs no LLM.
"""

from __future__ import annotations

import json
import os

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CategorizeSuggestion, KbDocument, KbVersion
from app.services.kb.automation import auto_job

# Frontmatter keys that signal the folder this note belongs in.
_CATEGORY_KEYS = ("category", "folder", "subfolder")


def _loads(raw: str | None) -> dict:
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


def category_for_document(doc: KbDocument) -> str | None:
    """Deterministic folder signal from frontmatter, or None.

    Returns a single-segment folder name (no slashes) so a proposal is always
    a *subfolder* move within the vault — never a path escape.
    """
    fm = _loads(doc.frontmatter_json) or {}
    for key in _CATEGORY_KEYS:
        val = fm.get(key)
        if val:
            val = str(val).strip("/").strip()
            if val and "/" not in val:
                return val
    return None


def _current_folder(doc: KbDocument) -> str:
    return os.path.dirname(doc.path_rel or "").strip("/")


def _proposed_path(doc: KbDocument, category: str) -> str:
    name = os.path.basename(doc.path_rel or f"doc-{doc.id}.md")
    return f"{category}/{name}"


def _has_proposal(db: Session, user_id: int, doc_id: int) -> bool:
    """Any prior proposal settles the doc — idempotency across nightly runs."""
    return (
        db.query(CategorizeSuggestion.id)
        .filter(
            CategorizeSuggestion.user_id == user_id,
            CategorizeSuggestion.document_id == doc_id,
        )
        .first()
        is not None
    )


@auto_job(
    "auto_categorize",
    toggle="KB_AUTO_CATEGORIZE_ENABLED",
    cap="KB_AUTO_CATEGORIZE_PER_RUN",
    description="Propose folder moves for notes with a frontmatter category/folder key.",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Scan newest-first for categorizeable docs and queue proposals."""
    if limit is None:
        limit = settings.KB_AUTO_CATEGORIZE_PER_RUN
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id)
        .order_by(KbDocument.id.desc())
        .limit(max(limit * 4, 20))  # oversample; filter on JSON below
        .all()
    )
    proposed = 0
    skipped = 0
    for doc in docs:
        if proposed >= limit:
            break
        category = category_for_document(doc)
        if not category:
            skipped += 1
            continue
        if _current_folder(doc) == category or _has_proposal(db, user_id, doc.id):
            skipped += 1
            continue
        db.add(
            CategorizeSuggestion(
                user_id=user_id,
                document_id=doc.id,
                proposed_path=_proposed_path(doc, category),
                rule="rule",
                status="pending",
            )
        )
        proposed += 1
    db.commit()
    return {"processed": proposed + skipped, "proposed": proposed, "skipped": skipped}


def _serialize(s: CategorizeSuggestion) -> dict:
    return {
        "id": s.id,
        "document_id": s.document_id,
        "proposed_path": s.proposed_path,
        "rule": s.rule,
        "status": s.status,
    }


def queue(db: Session, user_id: int, limit: int = 200) -> list[dict]:
    """Pending proposals for the user's review queue (newest first)."""
    rows = (
        db.query(CategorizeSuggestion)
        .filter(
            CategorizeSuggestion.user_id == user_id,
            CategorizeSuggestion.status == "pending",
        )
        .order_by(CategorizeSuggestion.id.asc())
        .limit(limit)
        .all()
    )
    return [_serialize(s) for s in rows]


def accept(db: Session, user_id: int, suggestion_ids: list[int]) -> int:
    """Apply approved moves: update ``path_rel`` + log the move in version history."""
    applied = 0
    for sid in suggestion_ids:
        s = (
            db.query(CategorizeSuggestion)
            .filter(
                CategorizeSuggestion.id == sid,
                CategorizeSuggestion.user_id == user_id,
            )
            .first()
        )
        if s is None or s.status != "pending":
            continue
        doc = (
            db.query(KbDocument)
            .filter(
                KbDocument.id == s.document_id,
                KbDocument.user_id == user_id,
            )
            .first()
        )
        if doc is None:
            continue
        # Version-history logging: record the structural change as a snapshot
        # entry so the history trail shows the move (content itself is unchanged).
        latest = (
            db.query(KbVersion)
            .filter(KbVersion.document_id == doc.id)
            .order_by(KbVersion.version_seq.desc())
            .first()
        )
        new_seq = (latest.version_seq if latest else 0) + 1
        old_path = doc.path_rel
        db.add(
            KbVersion(
                user_id=user_id,
                document_id=doc.id,
                version_seq=new_seq,
                content_hash=doc.content_hash,
                snapshot_text=(
                    f"[categorize:{s.id}] {old_path or ''} -> {s.proposed_path}"
                ),
            )
        )
        doc.path_rel = s.proposed_path
        s.status = "accepted"
        applied += 1
    db.commit()
    return applied


def reject(db: Session, user_id: int, suggestion_ids: list[int]) -> int:
    """Reject proposals — the doc stays put and is never re-proposed."""
    rejected = 0
    for sid in suggestion_ids:
        s = (
            db.query(CategorizeSuggestion)
            .filter(
                CategorizeSuggestion.id == sid,
                CategorizeSuggestion.user_id == user_id,
            )
            .first()
        )
        if s is not None and s.status == "pending":
            s.status = "rejected"
            rejected += 1
    db.commit()
    return rejected
