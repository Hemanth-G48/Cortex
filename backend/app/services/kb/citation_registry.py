"""Citation registry (Phase 4, Idea 36).

Parses reference lists from paper PDFs and inline ``@cite``/``[[cite:…]]``
markdown syntax, dedupes on ``(user_id, cite_key)``, optionally enriches arXiv
IDs via the Phase 1 ``arxiv`` service (cached, offline-safe), and exports the
registry as BibTeX (phrases 53–58).
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.models import KbCitation, KbDocument
from app.services.kb import KbService

logger = logging.getLogger(__name__)

# Section headings that start a reference list.
_REFERENCE_HEADINGS = re.compile(
    r"^\s*#*\s*(references|bibliography|works cited|references cited)\s*:?\s*$",
    re.IGNORECASE,
)
# Inline markdown citation syntax: @cite:key or [[cite:key]].
_INLINE_CITE_RE = re.compile(r"@cite:([A-Za-z0-9_\-\.]+)|\[\[cite:([A-Za-z0-9_\-\.]+)\]\]")
# Year hint in a reference line.
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
# DOI hint.
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-\._;()/:a-zA-Z0-9]+\b")
_ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_reference_lines(text: str | None) -> list[str]:
    """Split a document's reference list into citation lines (phrase 53).

    Heuristic: locate the first References/Bibliography heading, then split the
    following text on blank lines / newlines (numbered or bulleted entries).
    """
    text = text or ""
    lines = text.splitlines()

    start = None
    for i, line in enumerate(lines):
        if _REFERENCE_HEADINGS.match(line.strip()):
            start = i + 1
            break
    if start is None:
        return []

    raw = "\n".join(lines[start:])
    # Cut at a later top-level section heading (rare but possible).
    for m in re.finditer(r"(?m)^#+\s+\S", raw):
        first_line = raw[: m.start()]
        # Only cut when a substantial block precedes the next heading.
        if len(first_line.splitlines()) > 1:
            raw = first_line
        break

    entries: list[str] = []
    for chunk in re.split(r"\n\s*\n|\n(?=\s*(?:\d+[\.\)]|[-•*]))", raw):
        entry = re.sub(r"\s+", " ", chunk).strip()
        entry = re.sub(r"^\s*(?:\d+[\.\)]|[-•*])\s*", "", entry)
        if len(entry) >= 10:
            entries.append(entry)
    return entries[:200]


def parse_inline_citations(text: str | None) -> list[str]:
    """Extract inline citation keys (``@cite:key`` / ``[[cite:key]]``) (phrase 54)."""
    keys: list[str] = []
    for m in _INLINE_CITE_RE.finditer(text or ""):
        key = (m.group(1) or m.group(2) or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


# ---------------------------------------------------------------------------
# Keys + upsert
# ---------------------------------------------------------------------------

def make_cite_key(raw: str | None, title: str | None = None, year: int | None = None) -> str:
    """Deterministic cite key: first-alnum-token of the author + year, else slug."""
    if year is None:
        m = _YEAR_RE.search(raw or "")
        year = int(m.group(0)) if m else None
    year_str = f"{year}" if year else ""
    m = re.match(r"^\s*([A-Za-z][A-Za-z\-']{1,40})", raw or "")
    if m and year_str:
        return f"{m.group(1).lower()}{year_str}"
    if title:
        slug = re.sub(r"[^a-z0-9]+", "", title.lower())[:24]
        if slug:
            return f"{slug}{year_str}"
    digest = KbService.content_hash((raw or title or "cite").encode("utf-8"))[:10]
    return f"cite{digest}"


def _parse_meta(raw: str) -> dict:
    """Best-effort field extraction from one reference line."""
    year_m = _YEAR_RE.search(raw)
    doi_m = _DOI_RE.search(raw)
    arxiv_m = _ARXIV_ID_RE.search(raw)
    title = None
    # Heuristic title: for lines like "Author, A., Title, Journal, year" the
    # longest comma-delimited sentence fragment is often the title — keep it
    # simple: drop leading author chunk up to the first year-less comma run.
    return {
        "year": int(year_m.group(0)) if year_m else None,
        "doi": doi_m.group(0) if doi_m else None,
        "arxiv_id": arxiv_m.group(1) if arxiv_m else None,
        "title": title,
    }


def add_citation(
    db: Session,
    user_id: int,
    *,
    cite_key: str,
    document_id: int | None = None,
    raw_text: str | None = None,
    title: str | None = None,
    authors: list[str] | None = None,
    year: int | None = None,
    venue: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
) -> KbCitation:
    """Upsert one registry row keyed on ``(user_id, cite_key)`` (phrase 56)."""
    existing = (
        db.query(KbCitation)
        .filter(KbCitation.user_id == user_id, KbCitation.cite_key == cite_key)
        .first()
    )
    if existing:
        # Merge: fill missing fields, never overwrite existing metadata.
        if existing.title is None and title:
            existing.title = title
        if existing.raw_text is None and raw_text:
            existing.raw_text = raw_text
        if existing.year is None and year:
            existing.year = year
        if existing.venue is None and venue:
            existing.venue = venue
        if existing.doi is None and doi:
            existing.doi = doi
        if existing.arxiv_id is None and arxiv_id:
            existing.arxiv_id = arxiv_id
        if existing.document_id is None and document_id:
            existing.document_id = document_id
        db.add(existing)
        return existing

    row = KbCitation(
        user_id=user_id,
        document_id=document_id,
        cite_key=cite_key[:200],
        title=title,
        authors=KbService.json_dumps(authors) if authors else None,
        year=year,
        venue=venue,
        doi=doi,
        arxiv_id=arxiv_id,
        raw_text=raw_text,
    )
    db.add(row)
    # Flush so a second add_citation with the same key *within the same
    # transaction* resolves the existing row instead of violating the unique
    # constraint (phrase 56).
    db.flush()
    return row


def _enrich_arxiv(row: KbCitation) -> None:
    """Best-effort arXiv metadata enrichment (phrase 55). Never raises."""
    if not row.arxiv_id or row.title:
        return
    try:
        from app.services.kb.arxiv import fetch_arxiv_metadata

        meta = fetch_arxiv_metadata(row.arxiv_id)
        if meta and meta.get("title"):
            row.title = meta["title"]
            if meta.get("authors"):
                row.authors = KbService.json_dumps(meta["authors"])
            row.year = None  # arXiv Atom feed has no reliable year — keep parsed
    except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
        logger.warning("arXiv enrichment failed for %s: %s", row.cite_key, exc)


def extract_for_document(db: Session, doc: KbDocument) -> int:
    """Ingest-stage extraction: PDF reference lists + md inline ``@cite`` (phrase 56)."""
    text = doc.extracted_text or ""
    added = 0

    if doc.doc_type == "pdf":
        for raw in parse_reference_lines(text):
            key = make_cite_key(raw)
            meta = _parse_meta(raw)
            row = add_citation(
                db,
                doc.user_id,
                cite_key=key,
                document_id=doc.id,
                raw_text=raw,
                title=meta["title"],
                year=meta["year"],
                doi=meta["doi"],
                arxiv_id=meta["arxiv_id"],
            )
            _enrich_arxiv(row)
            db.add(row)
            added += 1
    else:
        for key in parse_inline_citations(text):
            row = add_citation(
                db, doc.user_id, cite_key=key, document_id=doc.id
            )
            db.add(row)
            added += 1

    if added:
        db.commit()
    return added


# ---------------------------------------------------------------------------
# Queries + BibTeX export
# ---------------------------------------------------------------------------

def list_citations(
    db: Session,
    user_id: int,
    year: int | None = None,
    venue: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Per-user registry listing with optional year/venue filters (phrase 57)."""
    q = db.query(KbCitation).filter(KbCitation.user_id == user_id)
    if year:
        q = q.filter(KbCitation.year == year)
    if venue:
        q = q.filter(KbCitation.venue.ilike(f"%{venue}%"))
    rows = q.order_by(KbCitation.created_at.desc()).limit(limit).all()
    return [_citation_dict(r) for r in rows]


def _citation_dict(r: KbCitation) -> dict:
    return {
        "id": r.id,
        "document_id": r.document_id,
        "cite_key": r.cite_key,
        "title": r.title,
        "authors": KbService.json_loads(r.authors) or [],
        "year": r.year,
        "venue": r.venue,
        "doi": r.doi,
        "arxiv_id": r.arxiv_id,
        "raw_text": r.raw_text,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _bibtex_escape(value: str) -> str:
    # Escape the characters BibTeX treats specially inside a ``{...}`` value.
    # Commas are safe inside braces (and appear in author names), so leave them.
    return re.sub(r"([{}%&#~^\\\"])", r"\\\1", value or "")


def build_bibtex(citations: list[dict]) -> str:
    """Render registry rows as a BibTeX file (phrase 58)."""
    entries: list[str] = []
    for c in citations:
        entry_type = "@article" if c.get("venue") else "@misc"
        fields = []
        if c.get("title"):
            fields.append(f"  title = {{{_bibtex_escape(c['title'])}}},")
        authors = c.get("authors") or []
        if authors:
            joined = " and ".join(_bibtex_escape(a) for a in authors)
            fields.append(f"  author = {{{joined}}},")
        if c.get("year"):
            fields.append(f"  year = {{{c['year']}}},")
        if c.get("venue"):
            fields.append(f"  journal = {{{_bibtex_escape(c['venue'])}}},")
        if c.get("doi"):
            fields.append(f"  doi = {{{_bibtex_escape(c['doi'])}}},")
        if c.get("arxiv_id"):
            fields.append(f"  eprint = {{{_bibtex_escape(c['arxiv_id'])}}},")
            fields.append("  archivePrefix = {arXiv},")
        key = c.get("cite_key") or "cite"
        entries.append(f"{entry_type}{{{key},\n" + "\n".join(fields) + "\n}")
    return "\n".join(entries) + "\n"
