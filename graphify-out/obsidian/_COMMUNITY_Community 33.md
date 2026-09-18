---
type: community
cohesion: 0.06
members: 58
---

# Community 33

**Cohesion:** 0.06 - loosely connected
**Members:** 58 nodes

## Members
- [[.test_char_ranges_are_valid_and_ordered()]] - code - backend/tests/test_kb_chunker.py
- [[.test_chunks_within_section_range()]] - code - backend/tests/test_kb_chunker.py
- [[.test_code_block_tags_are_excluded()]] - code - backend/tests/test_kb_markdown.py
- [[.test_daily_note_filename()]] - code - backend/tests/test_kb_markdown.py
- [[.test_detects_callout_types()]] - code - backend/tests/test_kb_markdown.py
- [[.test_deterministic_rechunk()]] - code - backend/tests/test_kb_chunker.py
- [[.test_empty_text_yields_no_chunks()]] - code - backend/tests/test_kb_chunker.py
- [[.test_heading_levels_text_and_offsets()]] - code - backend/tests/test_kb_markdown.py
- [[.test_headings_inside_code_fences_are_excluded()]] - code - backend/tests/test_kb_markdown.py
- [[.test_inline_and_nested_tags()]] - code - backend/tests/test_kb_markdown.py
- [[.test_no_frontmatter_yields_empty_dict()]] - code - backend/tests/test_kb_markdown.py
- [[.test_overlap_carryover()]] - code - backend/tests/test_kb_chunker.py
- [[.test_oversized_section_is_split()]] - code - backend/tests/test_kb_chunker.py
- [[.test_paragraph_split_without_outline()]] - code - backend/tests/test_kb_chunker.py
- [[.test_parses_known_and_custom_keys()]] - code - backend/tests/test_kb_markdown.py
- [[.test_sections_stay_intact()]] - code - backend/tests/test_kb_chunker.py
- [[.test_small_text_is_single_chunk()]] - code - backend/tests/test_kb_chunker.py
- [[.test_targets_strip_alias_and_fragments()]] - code - backend/tests/test_kb_markdown.py
- [[.test_url_hashes_are_not_tags()]] - code - backend/tests/test_kb_markdown.py
- [[Absolute span of a leading YAML frontmatter block, if present.]] - rationale - backend/app/services/kb/markdown_parser.py
- [[Chunk extracted text, capped at ``MAX_EXTRACTED_CHARS`` (phrase 66).]] - rationale - backend/app/services/kb/chunker.py
- [[Idea 4 — markdown parser tests frontmatter, wikilinks, tags, callouts, outline]] - rationale - backend/tests/test_kb_markdown.py
- [[Idea 7 — semantic (heading-aware) chunker tests.]] - rationale - backend/tests/test_kb_chunker.py
- [[KbChunkData]] - code - backend/app/services/kb/chunker.py
- [[KbMarkdown]] - code - backend/app/services/kb/markdown_parser.py
- [[Map heading outline → (heading_path, start, end) sections.]] - rationale - backend/app/services/kb/chunker.py
- [[Markdown parser — frontmatter, wikilinks, tags, callouts, outline (Idea 4).  Exp]] - rationale - backend/app/services/kb/markdown_parser.py
- [[OutlineItem]] - code - backend/app/services/kb/markdown_parser.py
- [[Parse Markdown source into structured knowledge metadata.]] - rationale - backend/app/services/kb/markdown_parser.py
- [[Return 'YYYY-MM-DD' when the filename is a daily note, else None.]] - rationale - backend/app/services/kb/markdown_parser.py
- [[Return (start, end) absolute char ranges inside fencedindented blocks.]] - rationale - backend/app/services/kb/markdown_parser.py
- [[Semantic (heading-aware) chunking (Idea 7).  Splits at H2H3 heading boundaries]] - rationale - backend/app/services/kb/chunker.py
- [[Split ``textstartend`` into ranges, paragraph-aware, with overlap.]] - rationale - backend/app/services/kb/chunker.py
- [[Split one oversized run at sentence boundaries with overlap.]] - rationale - backend/app/services/kb/chunker.py
- [[TestCallouts]] - code - backend/tests/test_kb_markdown.py
- [[TestDailyNotes]] - code - backend/tests/test_kb_markdown.py
- [[TestFrontmatter]] - code - backend/tests/test_kb_markdown.py
- [[TestHeadingSplits]] - code - backend/tests/test_kb_chunker.py
- [[TestNonMarkdownFallback]] - code - backend/tests/test_kb_chunker.py
- [[TestOutline]] - code - backend/tests/test_kb_markdown.py
- [[TestOversizedSections]] - code - backend/tests/test_kb_chunker.py
- [[TestTags]] - code - backend/tests/test_kb_markdown.py
- [[TestWikilinks]] - code - backend/tests/test_kb_markdown.py
- [[_code_block_ranges()]] - code - backend/app/services/kb/markdown_parser.py
- [[_frontmatter_span()]] - code - backend/app/services/kb/markdown_parser.py
- [[_hard_split()]] - code - backend/app/services/kb/chunker.py
- [[_heading_text()]] - code - backend/tests/test_kb_chunker.py
- [[_in_block()]] - code - backend/app/services/kb/markdown_parser.py
- [[_make()]] - code - backend/app/services/kb/chunker.py
- [[_sections_from_outline()]] - code - backend/app/services/kb/chunker.py
- [[_split_section()]] - code - backend/app/services/kb/chunker.py
- [[chunk_text()]] - code - backend/app/services/kb/chunker.py
- [[chunker.py]] - code - backend/app/services/kb/chunker.py
- [[daily_note_date()]] - code - backend/app/services/kb/markdown_parser.py
- [[markdown_parser.py]] - code - backend/app/services/kb/markdown_parser.py
- [[parse_markdown()]] - code - backend/app/services/kb/markdown_parser.py
- [[test_kb_chunker.py]] - code - backend/tests/test_kb_chunker.py
- [[test_kb_markdown.py]] - code - backend/tests/test_kb_markdown.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_33
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Community 48]]
- 2 edges to [[_COMMUNITY_Community 1]]
- 2 edges to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 71]]
- 1 edge to [[_COMMUNITY_Community 5]]
- 1 edge to [[_COMMUNITY_Community 38]]

## Top bridge nodes
- [[chunker.py]] - degree 13, connects to 4 communities
- [[markdown_parser.py]] - degree 12, connects to 2 communities
- [[parse_markdown()]] - degree 23, connects to 1 community
- [[chunk_text()]] - degree 17, connects to 1 community
- [[daily_note_date()]] - degree 5, connects to 1 community