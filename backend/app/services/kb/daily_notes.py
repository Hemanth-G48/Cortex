"""Daily-note integration (Phase 4, Idea 35).

- ``tag_daily_note`` — auto-tag ``YYYY-MM-DD.md`` vault docs with a
  ``daily/YYYY-MM-DD`` rule tag at ingest (phrase 42).
- ``get_daily_notes`` — aggregate a day's vault captures + schedule blocks +
  journal entries (phrases 43–44).
- ``get_today`` — convenience wrapper using the server date (phrase 45).
- ``append_daily_entry`` — write a line back into today's
  ``daily-life/YYYY-MM-DD.md`` note (audit defects #52, #66).
"""

from __future__ import annotations

import os
from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    DailyScheduleItem,
    JournalEntry,
    KbDocument,
    KbDocumentTag,
    KbTag,
)

# The ``kind`` stored on the auto-created KbTag (rules survive re-tagging).
_DAILY_KIND = "rule"

# Whether the post-ingest hook has been registered (register once, not on
# every call — the registry is a plain list).
_hook_registered = False


def register_hook_once() -> None:
    """Self-register as a post-ingest hook so pipeline.py doesn't need to know
    about daily notes. Best-effort and idempotent.
    """
    global _hook_registered
    if _hook_registered:
        return
    try:
        from app.services.kb.pipeline import register_post_ingest
        register_post_ingest("daily_notes.tag_daily_note", _daily_note_hook)
        _hook_registered = True
    except Exception:  # noqa: BLE001 — registration is best-effort
        pass


def _daily_note_hook(db: Session, doc: KbDocument) -> None:
    """Post-ingest hook: tag daily notes + award capture XP (phrase 42, 82)."""
    from app.models import User
    from app.services.kb.capture_xp import award_capture_xp

    tag_daily_note(db, doc)
    if doc.doc_date is not None:
        user = db.get(User, doc.user_id)
        if user is not None:
            award_capture_xp(db, user, "daily_note", f"doc:{doc.id}")
    db.commit()


def tag_daily_note(db: Session, doc: KbDocument) -> bool:
    """Attach a ``daily/YYYY-MM-DD`` tag to a daily-note document (phrase 42).

    Idempotent and cheap — no AI. Returns True when the tag was created.
    Also self-registers the post-ingest hook on first use.
    """
    register_hook_once()
    if doc.doc_type != "md" or doc.doc_date is None:
        return False
    name = f"daily/{doc.doc_date.isoformat()}"
    tag = (
        db.query(KbTag)
        .filter(KbTag.user_id == doc.user_id, KbTag.name == name)
        .first()
    )
    if tag is None:
        tag = KbTag(user_id=doc.user_id, name=name, kind=_DAILY_KIND)
        db.add(tag)
        db.flush()
    exists = (
        db.query(KbDocumentTag)
        .filter(
            KbDocumentTag.user_id == doc.user_id,
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.tag_id == tag.id,
        )
        .first()
    )
    if exists is None:
        db.add(
            KbDocumentTag(
                user_id=doc.user_id,
                document_id=doc.id,
                tag_id=tag.id,
                provenance="rule",
            )
        )
        db.flush()
        return True
    return False


def get_daily_notes(
    db: Session, user_id: int, day: date
) -> dict:
    """Aggregate one day's vault documents, schedule blocks, and journal entries."""
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.doc_date == day)
        .order_by(KbDocument.id.asc())
        .all()
    )
    schedule = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == user_id, DailyScheduleItem.date == day)
        .order_by(DailyScheduleItem.time_range.asc())
        .all()
    )
    journal = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id, JournalEntry.date == day)
        .order_by(JournalEntry.id.asc())
        .all()
    )
    return {
        "date": day.isoformat(),
        "documents": [
            {
                "id": d.id,
                "title": d.title or d.path_rel or f"doc {d.id}",
                "doc_type": d.doc_type,
                "char_count": d.char_count,
                "reading_time_seconds": d.reading_time_seconds,
                "quality_score": d.quality_score,
            }
            for d in docs
        ],
        "schedule": [
            {
                "id": s.id,
                "time_range": s.time_range,
                "activity": s.activity,
                "category": s.category,
                "done": s.done,
            }
            for s in schedule
        ],
        "journal": [
            {
                "id": j.id,
                "mood": j.mood,
                "content": (j.content or "")[:400],
                "tags": j.tags,
            }
            for j in journal
        ],
    }


def resolve_daily_life_root(db: Session, user_id: int) -> str | None:
    """Locate the vault's ``daily-life/`` folder from the registered sources.

    A source is rooted either at the vault itself or at the vault's ``notes/``
    folder (the vault migration repoints roots at ``notes/``). The non-knowledge
    daily-life area always sits beside ``notes/``. Returns ``None`` when no
    enabled source has a daily-life folder, so a caller never writes into a
    path it merely guessed.
    """
    from app.models import KbSource

    sources = (
        db.query(KbSource)
        .filter(KbSource.user_id == user_id, KbSource.enabled.is_(True))
        .order_by(KbSource.id)
        .all()
    )
    for source in sources:
        root = (source.root_path or "").strip()
        if not root:
            continue
        cleaned = root.rstrip("/\\")
        if os.path.basename(cleaned).casefold() == "notes":
            candidate = os.path.join(os.path.dirname(cleaned), "daily-life")
        else:
            candidate = os.path.join(cleaned, "daily-life")
        if os.path.isdir(candidate):
            return candidate
    return None


def append_daily_entry(
    db: Session,
    user_id: int,
    text: str,
    *,
    section: str | None = None,
    day: date | None = None,
) -> dict:
    """Append one line to today's ``daily-life/YYYY-MM-DD.md`` (defects #52, #66).

    Creates the note when it does not exist yet and inserts the line under
    ``## <section>`` (adding that heading when missing); with no section the line
    is appended at the end of the file. Returns ``{ok, date, path, created}`` and
    fails soft (``ok: False`` + ``reason``) when no vault daily-life folder is
    registered — never a 500 on a read-only or missing vault.
    """
    entry = (text or "").strip()
    if not entry:
        return {"ok": False, "reason": "empty entry", "date": None, "path": None, "created": False}
    root = resolve_daily_life_root(db, user_id)
    if root is None:
        return {
            "ok": False,
            "reason": "no daily-life folder found under the registered sources",
            "date": None,
            "path": None,
            "created": False,
        }
    day = day or date.today()
    target = os.path.join(root, f"{day.isoformat()}.md")
    created = not os.path.isfile(target)
    try:
        existing = ""
        if not created:
            with open(target, "r", encoding="utf-8") as fh:
                existing = fh.read()
        if section:
            updated = _insert_under_section(existing, section, entry)
        else:
            updated = f"{existing.rstrip()}\n{entry}\n" if existing.strip() else f"{entry}\n"
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(updated)
    except OSError as exc:  # unreadable/read-only vault — report, don't crash
        return {"ok": False, "reason": str(exc), "date": day.isoformat(), "path": target, "created": created}
    return {"ok": True, "reason": None, "date": day.isoformat(), "path": target, "created": created}


def _insert_under_section(content: str, section: str, entry: str) -> str:
    """Insert ``entry`` as the last bullet of ``## section`` (created if absent)."""
    heading = f"## {section}"
    lines = content.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().casefold() == heading.casefold():
            start = index
            break
    if start is None:
        prefix = content.rstrip()
        block = f"{heading}\n- {entry}"
        return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"
    # Find the end of this section (next level-1/2 heading) and append there.
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].lstrip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            end = index
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, f"- {entry}")
    return "\n".join(lines).rstrip() + "\n"


def get_today(db: Session, user_id: int) -> dict:
    """Server-date convenience wrapper (phrase 45)."""
    return get_daily_notes(db, user_id, date.today())
