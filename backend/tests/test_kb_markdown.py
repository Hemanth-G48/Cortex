"""Idea 4 — markdown parser tests: frontmatter, wikilinks, tags, callouts,
outline offsets, daily-note naming, and code-block exclusion.
"""
from __future__ import annotations

from app.services.kb.markdown_parser import daily_note_date, parse_markdown

FENCE = "```"
CODE_FENCE = f"{FENCE}python\n# not_a_tag_inside\n# Fake Heading\n{FENCE}"


NOTE = f"""---
title: My Note
tags: [front, matter]
aliases: [MN]
date: 2026-01-01
custom_key: keep me
---
# Introduction
Some text with [[target note]] and [[other|alias]] and [[note#section]].

## Section One
A #inline tag and a #nested/tag here.

> [!note] remember this
> [!warning] careful

{CODE_FENCE}

#tag-after-fence
"""


class TestFrontmatter:
    def test_parses_known_and_custom_keys(self):
        md = parse_markdown(NOTE)
        assert md.frontmatter["title"] == "My Note"
        # YAML parses bare dates as date objects; stringify before comparison.
        assert str(md.frontmatter["date"]) == "2026-01-01"
        assert md.frontmatter["custom_key"] == "keep me"
        assert "front" in md.frontmatter["tags"]

    def test_no_frontmatter_yields_empty_dict(self):
        md = parse_markdown("# Just a heading\n")
        assert md.frontmatter == {}


class TestWikilinks:
    def test_targets_strip_alias_and_fragments(self):
        md = parse_markdown(NOTE)
        assert "target note" in md.wikilinks
        assert "other" in md.wikilinks  # [[other|alias]]
        assert "note" in md.wikilinks  # [[note#section]] → fragment stripped


class TestTags:
    def test_inline_and_nested_tags(self):
        md = parse_markdown(NOTE)
        assert "inline" in md.tags
        assert "nested/tag" in md.tags
        assert "tag-after-fence" in md.tags

    def test_code_block_tags_are_excluded(self):
        md = parse_markdown(NOTE)
        assert "not_a_tag_inside" not in md.tags

    def test_url_hashes_are_not_tags(self):
        md = parse_markdown("Visit https://example.com/page#section now\n")
        assert all(not t.endswith("section") for t in md.tags)


class TestCallouts:
    def test_detects_callout_types(self):
        md = parse_markdown(NOTE)
        assert "note" in md.callouts
        assert "warning" in md.callouts


class TestOutline:
    def test_heading_levels_text_and_offsets(self):
        md = parse_markdown(NOTE)
        assert md.outline[0].level == 1
        assert md.outline[0].text == "Introduction"
        assert md.outline[0].char_start >= 0
        levels = [o.level for o in md.outline]
        assert levels == [1, 2]
        assert md.outline[1].text == "Section One"
        # Offsets increase monotonically.
        starts = [o.char_start for o in md.outline]
        assert starts == sorted(starts)

    def test_headings_inside_code_fences_are_excluded(self):
        md = parse_markdown(NOTE)
        assert "Fake Heading" not in [o.text for o in md.outline]


class TestDailyNotes:
    def test_daily_note_filename(self):
        assert daily_note_date("2026-07-04.md") == "2026-07-04"
        assert daily_note_date("notes.md") is None
        assert daily_note_date("2026-7-4.md") is None  # zero-padded only
