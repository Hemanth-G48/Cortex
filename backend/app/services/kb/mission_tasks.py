"""Vault-derived subtask suggestions for a Mission (audit defect #80).

A Mission has no stored link to a course or document, so we find the vault
material that describes the same work: run the existing hybrid search for the
mission title, then mine the top documents' chunks for actionable lines —
markdown checklist items first (``- [ ]`` / ``- [x]``), falling back to the
document outline (``## Heading``) when a note has no explicit checklist.

Read-only: nothing is written. The frontend shows the suggestions and creates a
real ``MissionTask`` only when the user accepts one.
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument
from app.services.kb.search import KbSearcher

MAX_DOCS = 5
MAX_SUGGESTIONS = 8

_CHECKBOX = re.compile(r"^\s*[-*+]\s*\[(?: |x|X)\]\s+(?P<text>.+?)\s*$")
_HEADING = re.compile(r"^\s{0,3}#{2,4}\s+(?P<text>.+?)\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(?P<text>.+?)\s*$")

# Headings that are structural rather than actionable.
_SKIP_HEADINGS = {
    "introduction", "overview", "summary", "conclusion", "references",
    "table of contents", "contents", "notes", "appendix",
}


def _clean(text: str) -> str:
    """Strip markdown emphasis/links so a suggestion reads as a plain task."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text.strip(" .-–—:\t")


def _extract_from_chunks(
    chunks: list[KbChunk],
) -> list[tuple[str, str]]:
    """Return ``(kind, text)`` pairs in document order, checklists first."""
    checkboxes: list[tuple[str, str]] = []
    headings: list[tuple[str, str]] = []
    bullets: list[tuple[str, str]] = []

    for chunk in chunks:
        for raw in (chunk.content or "").splitlines():
            m = _CHECKBOX.match(raw)
            if m:
                text = _clean(m.group("text"))
                if text:
                    checkboxes.append(("checklist", text))
                continue
            h = _HEADING.match(raw)
            if h:
                text = _clean(h.group("text"))
                if text and text.lower() not in _SKIP_HEADINGS:
                    headings.append(("outline", text))
                continue
            b = _BULLET.match(raw)
            if b:
                text = _clean(b.group("text"))
                # Only promote short, imperative-looking bullets.
                if text and 3 <= len(text) <= 120:
                    bullets.append(("bullet", text))

    if checkboxes:
        return checkboxes
    if headings:
        return headings
    return bullets


def vault_task_suggestions(
    db: Session, user_id: int, mission_title: str, limit: int = MAX_SUGGESTIONS
) -> dict[str, Any]:
    """Search the vault for the mission and mine actionable subtask lines."""
    query = (mission_title or "").strip()
    if not query:
        return {"query": query, "suggestions": [], "documents": []}

    searcher = KbSearcher(db, user_id)
    try:
        result = searcher.search(query, mode="hybrid", limit=MAX_DOCS)
    except Exception:  # noqa: BLE001 — suggestions must never break the card
        return {"query": query, "suggestions": [], "documents": []}

    doc_ids: list[int] = []
    for item in result.get("items", []):
        doc_id = item.get("document_id")
        if isinstance(doc_id, int) and doc_id not in doc_ids:
            doc_ids.append(doc_id)
    if not doc_ids:
        return {"query": query, "suggestions": [], "documents": []}

    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.id.in_(doc_ids[:MAX_DOCS]))
        .all()
    )
    by_id = {d.id: d for d in docs}

    seen: set[str] = set()
    suggestions: list[dict[str, Any]] = []
    used_docs: dict[int, str] = {}

    for doc_id in doc_ids[:MAX_DOCS]:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        chunks = (
            db.query(KbChunk)
            .filter(KbChunk.document_id == doc_id, KbChunk.user_id == user_id)
            .order_by(KbChunk.seq)
            .all()
        )
        for kind, text in _extract_from_chunks(chunks):
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "title": text[:200],
                    "kind": kind,
                    "document_id": doc_id,
                    "document_title": doc.title,
                }
            )
            used_docs[doc_id] = doc.title or f"Document {doc_id}"
            if len(suggestions) >= limit:
                break
        if len(suggestions) >= limit:
            break

    return {
        "query": query,
        "suggestions": suggestions,
        "documents": [
            {"id": did, "title": title} for did, title in used_docs.items()
        ],
    }
