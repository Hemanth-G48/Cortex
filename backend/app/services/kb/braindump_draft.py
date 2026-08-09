"""Brain dump → structured note migration (Phase 4, Idea 40).

The single-row ``BrainDump`` stays the source of truth for the widget; every
save also upserts a draft ``KbDocument`` (``status='draft'``, origin flagged in
``metadata_json``) so the capture can be filed, tagged, and AI-split (phrases
91–95). Fully backward-compatible — the widget UX is untouched (phrase 96).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import KbDocument, KbTag, KbDocumentTag
from app.services.ai_fallback import demo_braindump_split
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.pipeline import re_chunk

logger = logging.getLogger(__name__)

ORIGIN = "braindump"


def _is_braindump_draft(doc: KbDocument) -> bool:
    meta = KbService.json_loads(doc.metadata_json) or {}
    return meta.get("origin") == ORIGIN


def find_draft(db: Session, user_id: int) -> KbDocument | None:
    """The user's current braindump draft (None when never saved)."""
    for d in (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.status == "draft")
        .all()
    ):
        if _is_braindump_draft(d):
            return d
    return None


def upsert_draft(db: Session, user_id: int, content: str | None) -> KbDocument | None:
    """Upsert the draft document from a brain-dump save (phrase 91).

    Idempotent: repeated saves (debounced autosave) converge on the same row,
    re-chunking the updated text. Returns None when content is empty so the
    widget never creates empty drafts.
    """
    content = (content or "").strip()
    if not content:
        return None

    doc = find_draft(db, user_id)
    digest = KbService.content_hash(content.encode("utf-8"))
    if doc is None:
        doc = KbDocument(
            user_id=user_id,
            title=content[:80],
            doc_type="md",
            status="draft",
            extracted_text=content,
            char_count=len(content),
            content_hash=digest,
            metadata_json=KbService.json_dumps({"origin": ORIGIN}),
        )
        db.add(doc)
        db.flush()
    else:
        if doc.content_hash == digest and doc.extracted_text == content:
            return doc  # no-op save
        doc.extracted_text = content
        doc.char_count = len(content)
        doc.title = content[:80]
        doc.content_hash = digest

    re_chunk(db, doc)
    db.commit()
    db.refresh(doc)
    return doc


def file_draft(
    db: Session,
    user_id: int,
    document_id: int,
    *,
    title: str | None = None,
    source_id: int | None = None,
    tags: list[str] | None = None,
) -> KbDocument:
    """Quick-file: title it, attach tags, move ``draft`` → ``new`` (phrase 94)."""
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")
    if doc.status != "draft" or not _is_braindump_draft(doc):
        raise HTTPException(400, "Document is not a braindump draft")

    if title and title.strip():
        doc.title = title.strip()[:500]
    if source_id is not None:
        from app.services.kb import KbService as Kb

        source = Kb.get_source(db, user_id, source_id)
        if source is None:
            raise HTTPException(404, "Source not found")
        doc.source_id = source.id

    # Attach tags (create-or-reuse rule tags) and clear the origin marker.
    for name in tags or []:
        name = name.strip().lower()[:40]
        if not name:
            continue
        tag = (
            db.query(KbTag)
            .filter(KbTag.user_id == user_id, KbTag.name == name)
            .first()
        )
        if tag is None:
            tag = KbTag(user_id=user_id, name=name, kind="rule")
            db.add(tag)
            db.flush()
        exists = (
            db.query(KbDocumentTag)
            .filter(
                KbDocumentTag.user_id == user_id,
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag.id,
            )
            .first()
        )
        if exists is None:
            db.add(
                KbDocumentTag(
                    user_id=user_id,
                    document_id=doc.id,
                    tag_id=tag.id,
                    provenance="rule",
                )
            )

    meta = KbService.json_loads(doc.metadata_json) or {}
    meta.pop("origin", None)
    doc.metadata_json = KbService.json_dumps(meta) if meta else None
    doc.status = "new"
    doc.indexed_at = None
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def split_draft(db: Session, user_id: int, document_id: int) -> dict:
    """AI-assisted section proposals applied to the draft as headings (phrase 95)."""
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")
    if not _is_braindump_draft(doc):
        raise HTTPException(400, "Document is not a braindump draft")
    if len(doc.extracted_text or "") < 400:
        raise HTTPException(422, "Text is too short to split")

    from app.services.ai_client import ai_available

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, user_id):
        raise HTTPException(429, "Daily generation budget exhausted — try again tomorrow.")

    sections: list[dict] = []
    if not used_fallback:
        try:
            from app.services.ai_client import generate_json
            from app.services.prompts import braindump_split_prompt

            parsed = generate_json(
                braindump_split_prompt(doc.extracted_text),
                max_tokens=1200,
                temperature=0.3,
            )
            raw = parsed.get("sections") if isinstance(parsed, dict) else parsed
            if isinstance(raw, list):
                sections = [
                    {
                        "title": str(s.get("title") or "Section").strip()[:120],
                        "char_start": max(0, int(s.get("char_start") or 0)),
                    }
                    for s in raw
                    if isinstance(s, dict)
                ]
                sections = [s for s in sections if 0 <= s["char_start"] <= len(doc.extracted_text or "")]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Brain-dump split failed for doc %s: %s", doc.id, exc)
            sections = []

    if not sections:
        used_fallback = True
        sections = demo_braindump_split(doc.extracted_text)

    if not used_fallback:
        record_generation(db, user_id, "split")

    # Apply headings by inserting ``# title`` lines at the section starts.
    text = doc.extracted_text or ""
    if sections and len(sections) > 1:
        inserts = sorted(
            ((s["char_start"], s["title"]) for s in sections if s["char_start"] > 0),
            key=lambda t: t[0],
        )
        offset = 0
        for pos, title in inserts:
            text = text[: pos + offset] + f"\n\n# {title}\n" + text[pos + offset :]
            offset += len(title) + 7
        doc.extracted_text = text
        doc.char_count = len(text)
        doc.content_hash = KbService.content_hash(text.encode("utf-8"))
        re_chunk(db, doc)
        db.add(doc)
        db.commit()

    return {
        "document_id": doc.id,
        "sections_applied": max(0, len(sections) - 1),
        "fallback": used_fallback,
        "sections": sections,
    }
