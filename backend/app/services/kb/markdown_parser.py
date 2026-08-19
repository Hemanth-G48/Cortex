"""Markdown parser — frontmatter, wikilinks, tags, callouts, outline (Idea 4).

Exposes :func:`parse_markdown` returning a :class:`KbMarkdown` dataclass. All
char offsets are absolute into the raw source text so the chunker (Idea 7) can
keep sections intact and Phase 3 search can highlight exact ranges.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import frontmatter as fm

WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")
# Inline tag: plain ``#tag`` / ``#nested/tag`` OR a ``course:<name>`` tag that
# may contain spaces (e.g. ``#course:Operating Systems``). The ``course:``
# alternative is tried first so ``#course:X`` is never split into ``course`` + X.
# Course tags capture word chars, spaces, and ``. & ' -`` until the next
# character that isn't part of a tag (punctuation, another ``#``, EOL).
TAG_RE = re.compile(
    r"(?:^|[\s(])#("
    r"course:[A-Za-z0-9_][A-Za-z0-9_ .&'-]*"
    r"|[A-Za-z0-9_][A-Za-z0-9_/.\-]*"
    r")"
)
CALLOUT_RE = re.compile(r"^>\s*\[!(\w+)\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
DAILY_NOTE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")


@dataclass
class OutlineItem:
    level: int
    text: str
    char_start: int


@dataclass
class KbMarkdown:
    frontmatter: dict = field(default_factory=dict)
    wikilinks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    callouts: list[str] = field(default_factory=list)
    outline: list[OutlineItem] = field(default_factory=list)
    # Absolute char ranges of fenced/indented code blocks.
    code_block_ranges: list[tuple[int, int]] = field(default_factory=list)


def _code_block_ranges(text: str) -> list[tuple[int, int]]:
    """Return (start, end) absolute char ranges inside fenced/indented blocks."""
    ranges: list[tuple[int, int]] = []
    fence_char: str | None = None
    fence_len = 0
    pos = 0
    indent_active = False
    indent_start = 0
    for line in text.splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if m and not indent_active:
            if fence_char is None:
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
                ranges.append([pos, pos + len(line)])
            elif m.group(1)[0] == fence_char and len(m.group(1)) >= fence_len:
                ranges[-1][1] = pos + len(line)
                fence_char = None
        elif fence_char is None:
            if line.startswith(("    ", "\t")):
                if not indent_active:
                    indent_active = True
                    indent_start = pos
            elif indent_active:
                ranges.append([indent_start, pos])
                indent_active = False
        pos += len(line)
    if indent_active:
        ranges.append([indent_start, pos])
    return [tuple(r) for r in ranges]


def _frontmatter_span(text: str) -> tuple[int, int] | None:
    """Absolute span of a leading YAML frontmatter block, if present."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines(keepends=True)
    if len(lines) < 2:
        return None
    pos = len(lines[0])
    for line in lines[1:]:
        if line.rstrip("\r\n").strip() in ("---", "..."):
            return (0, pos + len(line))
        pos += len(line)
    return None


def _in_block(pos: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in ranges)


def parse_markdown(text: str) -> KbMarkdown:
    """Parse Markdown source into structured knowledge metadata."""
    md = KbMarkdown()

    # --- Frontmatter (YAML) via python-frontmatter ---
    try:
        parsed = fm.loads(text)
        md.frontmatter = dict(parsed.metadata or {})
    except Exception:
        pass

    fm_span = _frontmatter_span(text)
    md.code_block_ranges = _code_block_ranges(text)
    raw_lines = text.splitlines(keepends=True)

    def skip(pos: int) -> bool:
        if fm_span and fm_span[0] <= pos < fm_span[1]:
            return True
        return _in_block(pos, md.code_block_ranges)

    # --- Wikilinks [[target]] / [[target|alias]] / [[note#heading]] ---
    for raw in WIKILINK_RE.findall(text):
        target = raw.split("|")[0].strip()
        # Normalize targets to relative vault paths: strip #heading fragments
        # so Phase 2 kb_edges resolution matches clean note paths (phrase 34).
        md.wikilinks.append(target.split("#")[0])

    # --- Inline tags (#tag and #nested/tag) outside frontmatter/code ---
    pos = 0
    for line in raw_lines:
        if not skip(pos):
            for m in TAG_RE.finditer(line):
                md.tags.append(m.group(1))
        pos += len(line)

    # --- Callouts (> [!note] ...) ---
    for line in text.splitlines():
        m = CALLOUT_RE.match(line.strip())
        if m:
            md.callouts.append(m.group(1).lower())

    # --- Heading outline with absolute offsets ---
    pos = 0
    for line in raw_lines:
        if not skip(pos):
            m = HEADING_RE.match(line)
            if m:
                md.outline.append(
                    OutlineItem(level=len(m.group(1)), text=m.group(2).strip(), char_start=pos)
                )
        pos += len(line)

    return md


def daily_note_date(filename: str) -> str | None:
    """Return 'YYYY-MM-DD' when the filename is a daily note, else None."""
    m = DAILY_NOTE_RE.match(filename)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
