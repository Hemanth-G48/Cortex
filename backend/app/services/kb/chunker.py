"""Semantic (heading-aware) chunking (Idea 7).

Splits at H2/H3 heading boundaries from the Idea 4 outline so sections stay
intact, merges small sections, and splits oversized ones at paragraph/sentence
boundaries with ``KB_CHUNK_OVERLAP`` carry-over. Emits absolute ``char_start``
/ ``char_end`` per chunk plus a ``token_estimate`` (≈ chars/4) — the Phase 2
embedding seam.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings
from app.services.ingestion import MAX_EXTRACTED_CHARS
from app.services.kb import KbService

SENTENCE_BREAK_RE = re.compile(r"[.!?]\s+|\n")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


@dataclass
class KbChunkData:
    content: str
    char_start: int
    char_end: int
    heading_path: str | None
    token_estimate: int


def _make(text: str, start: int, end: int, heading_path: str | None) -> KbChunkData:
    content = text[start:end]
    return KbChunkData(
        content=content,
        char_start=start,
        char_end=end,
        heading_path=heading_path,
        token_estimate=KbService.token_estimate(content),
    )


def _sections_from_outline(
    text: str, outline: list
) -> list[tuple[str | None, int, int]]:
    """Map heading outline → (heading_path, start, end) sections."""
    boundaries = sorted(outline, key=lambda o: o.char_start)
    sections: list[tuple[str | None, int, int]] = []
    if not boundaries:
        return [(None, 0, len(text))]

    # Content before the first heading keeps its own section.
    first = boundaries[0]
    if first.char_start > 0:
        sections.append((None, 0, first.char_start))

    active: list[tuple[int, str]] = []
    for i, item in enumerate(boundaries):
        while active and active[-1][0] >= item.level:
            active.pop()
        active.append((item.level, item.text))
        path = " > ".join(name for _, name in active)
        end = boundaries[i + 1].char_start if i + 1 < len(boundaries) else len(text)
        sections.append((path, item.char_start, end))
    return sections


def _split_section(
    text: str, start: int, end: int, chunk_size: int, overlap: int
) -> list[tuple[int, int]]:
    """Split ``text[start:end]`` into ranges, paragraph-aware, with overlap."""
    section = text[start:end]
    n = len(section)
    if n <= chunk_size:
        return [(start, end)]

    # Paragraph boundaries (blank-line gaps excluded from chunk contents).
    paras: list[tuple[int, int]] = []
    p_start = 0
    for m in PARAGRAPH_SPLIT_RE.finditer(section):
        paras.append((p_start, m.start()))
        p_start = m.end()
    paras.append((p_start, n))

    ranges: list[tuple[int, int]] = []
    cur_start, cur_end = paras[0]
    for p_start, p_end in paras[1:]:
        if (cur_end - cur_start) + (p_end - cur_end) <= chunk_size:
            cur_end = p_end
        else:
            # If the pending paragraph alone is oversized, hard-split it first.
            if p_end - p_start > chunk_size:
                ranges.extend(_hard_split(section, cur_start, p_end, chunk_size, overlap))
                cur_start = max(0, p_end - overlap)
                cur_end = cur_start
            else:
                ranges.append((cur_start, cur_end))
                carry = min(overlap, cur_end - cur_start)
                cur_start = max(p_start - carry, 0)
                cur_end = p_end
    if cur_end > cur_start:
        if cur_end - cur_start > chunk_size:
            ranges.extend(_hard_split(section, cur_start, cur_end, chunk_size, overlap))
        else:
            ranges.append((cur_start, cur_end))

    # Rebase from section-relative to document-absolute offsets.
    return [(start + s, start + e) for s, e in ranges]


def _hard_split(
    section: str, start: int, end: int, chunk_size: int, overlap: int
) -> list[tuple[int, int]]:
    """Split one oversized run at sentence boundaries with overlap."""
    pieces: list[tuple[int, int]] = []
    i = start
    n = end
    while i < n:
        limit = min(i + chunk_size, n)
        window = section[i:limit]
        best = limit - i
        for m in SENTENCE_BREAK_RE.finditer(window):
            if m.end() <= chunk_size and m.end() >= chunk_size // 2:
                best = m.end()
        pieces.append((i, i + best))
        if i + best >= n:
            break
        i = max(i + 1, i + best - overlap)
    return pieces


def chunk_text(
    text: str | None,
    outline: list | None = None,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[KbChunkData]:
    """Chunk extracted text, capped at ``MAX_EXTRACTED_CHARS`` (phrase 66)."""
    chunk_size = chunk_size or settings.KB_CHUNK_SIZE
    overlap = overlap if overlap is not None else settings.KB_CHUNK_OVERLAP
    raw = (text or "")[:MAX_EXTRACTED_CHARS]
    if not raw.strip():
        return []

    if outline:
        sections = _sections_from_outline(raw, outline)
        # Merge small trailing sections into the previous one (phrase 63).
        merged: list[tuple[str | None, int, int]] = []
        for path, s, e in sections:
            if merged:
                prev_path, ps, pe = merged[-1]
                if (e - s) < chunk_size * 0.25 and (e - s) + (pe - ps) <= chunk_size:
                    merged[-1] = (prev_path, ps, e)
                    continue
            merged.append((path, s, e))
    else:
        merged = [(None, 0, len(raw))]

    chunks: list[KbChunkData] = []
    for path, s, e in merged:
        if e - s <= chunk_size:
            chunks.append(_make(raw, s, e, path))
        else:
            for s2, e2 in _split_section(raw, s, e, chunk_size, overlap):
                chunks.append(_make(raw, s2, e2, path))
    return chunks
