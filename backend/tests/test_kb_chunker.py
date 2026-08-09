"""Idea 7 — semantic (heading-aware) chunker tests."""
from __future__ import annotations

from app.services.kb.chunker import chunk_text
from app.services.kb.markdown_parser import parse_markdown


def _heading_text():
    return (
        "# Intro\n"
        + ("intro body. " * 12) + "\n"          # ~ 140 chars
        + "## Alpha\n"
        + ("alpha body. " * 40) + "\n"          # ~ 450 chars
        + "## Beta\n"
        + ("beta body. " * 40) + "\n"
        + "### Gamma\n"
        + ("gamma body. " * 40) + "\n"
    )


class TestHeadingSplits:
    def test_sections_stay_intact(self):
        text = _heading_text()
        chunks = chunk_text(text, outline=parse_markdown(text).outline)
        paths = [c.heading_path for c in chunks]
        assert "Intro > Alpha" in paths
        assert "Intro > Beta" in paths
        assert "Intro > Beta > Gamma" in paths
        assert any(p is not None and p.startswith("Intro") for p in paths)

    def test_char_ranges_are_valid_and_ordered(self):
        text = _heading_text()
        chunks = chunk_text(text, outline=parse_markdown(text).outline)
        prev_end = 0
        for c in chunks:
            assert 0 <= c.char_start < c.char_end <= len(text)
            assert c.char_start >= prev_end
            assert c.content == text[c.char_start:c.char_end]
            prev_end = c.char_end

    def test_deterministic_rechunk(self):
        text = _heading_text()
        outline = parse_markdown(text).outline
        a = chunk_text(text, outline=outline)
        b = chunk_text(text, outline=outline)
        assert [(c.content, c.char_start, c.char_end) for c in a] == \
            [(c.content, c.char_start, c.char_end) for c in b]


class TestOversizedSections:
    def test_oversized_section_is_split(self):
        text = "# Big\n" + "word " * 3000  # single-line giant paragraph
        outline = parse_markdown(text).outline
        chunks = chunk_text(text, outline=outline, chunk_size=1200, overlap=150)
        assert len(chunks) > 1
        for c in chunks:
            assert c.char_end - c.char_start <= 1200 + 150

    def test_overlap_carryover(self):
        text = "word " * 3000
        chunks = chunk_text(text, chunk_size=1200, overlap=150)
        assert len(chunks) > 1
        first, second = chunks[0], chunks[1]
        assert second.content[:150] == first.content[-150:]

    def test_chunks_within_section_range(self):
        text = "# Big\n" + "word " * 3000
        outline = parse_markdown(text).outline
        chunks = chunk_text(text, outline=outline, chunk_size=1200, overlap=0)
        section_start = outline[0].char_start
        for c in chunks:
            assert c.char_start >= section_start


class TestNonMarkdownFallback:
    def test_paragraph_split_without_outline(self):
        text = "p one.\n\np two.\n\np three."
        chunks = chunk_text(text, chunk_size=10, overlap=0)
        assert [c.content for c in chunks] == ["p one.", "p two.", "p three."]

    def test_small_text_is_single_chunk(self):
        chunks = chunk_text("tiny note", chunk_size=1200)
        assert len(chunks) == 1
        assert chunks[0].content == "tiny note"
        assert chunks[0].token_estimate >= 1

    def test_empty_text_yields_no_chunks(self):
        assert chunk_text("") == []
        assert chunk_text(None) == []
