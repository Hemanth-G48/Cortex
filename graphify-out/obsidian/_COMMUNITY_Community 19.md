---
type: community
cohesion: 0.05
members: 81
---

# Community 19

**Cohesion:** 0.05 - loosely connected
**Members:** 81 nodes

## Members
- [[.test_author_filter()]] - code - backend/tests/test_kb_metadata.py
- [[.test_code_like_text_returns_none()]] - code - backend/tests/test_kb_metadata.py
- [[.test_date_range_filter()]] - code - backend/tests/test_kb_metadata.py
- [[.test_deterministic_language_set_by_enrich()]] - code - backend/tests/test_kb_metadata.py
- [[.test_empty_frontmatter()]] - code - backend/tests/test_kb_metadata.py
- [[.test_empty_text_returns_none()]] - code - backend/tests/test_kb_metadata.py
- [[.test_english_detection()]] - code - backend/tests/test_kb_metadata.py
- [[.test_exact_200_words()]] - code - backend/tests/test_kb_metadata.py
- [[.test_fractional_rounds_down()]] - code - backend/tests/test_kb_metadata.py
- [[.test_french_detection()]] - code - backend/tests/test_kb_metadata.py
- [[.test_frontmatter_author_in_proposal()]] - code - backend/tests/test_kb_metadata.py
- [[.test_frontmatter_author_wins()]] - code - backend/tests/test_kb_metadata.py
- [[.test_frontmatter_language_and_date()]] - code - backend/tests/test_kb_metadata.py
- [[.test_frontmatter_precedence_over_llm()]] - code - backend/tests/test_kb_metadata.py
- [[.test_frontmatter_source_url()]] - code - backend/tests/test_kb_metadata.py
- [[.test_language_filter()]] - code - backend/tests/test_kb_metadata.py
- [[.test_manual_override_persists()]] - code - backend/tests/test_kb_metadata.py
- [[.test_manual_override_survives_re_enrich()]] - code - backend/tests/test_kb_metadata.py
- [[.test_metadata_dict_merged()]] - code - backend/tests/test_kb_metadata.py
- [[.test_no_filters_returns_all()_1]] - code - backend/tests/test_kb_metadata.py
- [[.test_proposal_404_for_other_user()]] - code - backend/tests/test_kb_metadata.py
- [[.test_proposal_get_never_calls_llm()]] - code - backend/tests/test_kb_metadata.py
- [[.test_proposal_returns_metadata()]] - code - backend/tests/test_kb_metadata.py
- [[.test_provenance_stored_in_metadata_json()]] - code - backend/tests/test_kb_metadata.py
- [[.test_put_metadata_404_for_other_user()]] - code - backend/tests/test_kb_metadata.py
- [[.test_put_metadata_manual_override()]] - code - backend/tests/test_kb_metadata.py
- [[.test_returns_valid_proposal_when_ai_disabled()]] - code - backend/tests/test_kb_metadata.py
- [[.test_zero_text()]] - code - backend/tests/test_kb_metadata.py
- [[404 when requesting proposal for another user's document.]] - rationale - backend/tests/test_kb_metadata.py
- [[404 when updating another user's document.]] - rationale - backend/tests/test_kb_metadata.py
- [[Any_13]] - code
- [[Apply a manual metadata override to a document.      Writes provided fields into]] - rationale - backend/app/services/kb/metadata.py
- [[Apply metadata filters to a ``KbDocument`` SQLAlchemy query.      Each non-None]] - rationale - backend/app/services/kb/metadata.py
- [[Enrich a document's metadata in-place and commit.      Merge rule manual  fron]] - rationale - backend/app/services/kb/metadata.py
- [[Frontmatter author beats LLM proposal (phrase 27).]] - rationale - backend/tests/test_kb_metadata.py
- [[GET metadata-proposal is read-only — browsing must not spend an         LLM call]] - rationale - backend/tests/test_kb_metadata.py
- [[GET proposal returns a valid KbMetadataProposal.]] - rationale - backend/tests/test_kb_metadata.py
- [[KbDocument_18]] - code
- [[KbDocument_46]] - code
- [[KbMetadataUpdate_1]] - code - backend/app/schemas/kb.py
- [[KbMetadataUpdate_2]] - code
- [[Manual override must not be overwritten by re-ingest (phrase 27).]] - rationale - backend/tests/test_kb_metadata.py
- [[Metadata extraction & enrichment (Idea 13, phrases 22-27, 30).  Provides determi]] - rationale - backend/app/services/kb/metadata.py
- [[PUT metadata stores manual override; re-enrich preserves it.]] - rationale - backend/tests/test_kb_metadata.py
- [[PUT metadata stores values in metadata_jsonmanual (phrase 26).]] - rationale - backend/tests/test_kb_metadata.py
- [[Per-field provenance is persisted in metadata_json (phrase 27).]] - rationale - backend/tests/test_kb_metadata.py
- [[Propose metadata for a document, merging frontmatter + LLM + heuristics.      St]] - rationale - backend/app/services/kb/metadata.py
- [[Pull metadata fields from ``doc.frontmatter_json``.      Frontmatter always wins]] - rationale - backend/app/services/kb/metadata.py
- [[Return True if any field's provenance indicates AI involvement.]] - rationale - backend/app/services/kb/metadata.py
- [[Return a 2-letter language code or None using deterministic heuristics.      Tok]] - rationale - backend/app/services/kb/metadata.py
- [[Return estimated reading time in seconds (words  200 wpm, min 0).]] - rationale - backend/app/services/kb/metadata.py
- [[Session_168]] - code
- [[Session_234]] - code
- [[TestApplyMetadataUpdate]] - code - backend/tests/test_kb_metadata.py
- [[TestDetectLanguage]] - code - backend/tests/test_kb_metadata.py
- [[TestEnrichMetadata]] - code - backend/tests/test_kb_metadata.py
- [[TestEstimateReadingTime]] - code - backend/tests/test_kb_metadata.py
- [[TestExtractFrontmatter]] - code - backend/tests/test_kb_metadata.py
- [[TestMetadataApi]] - code - backend/tests/test_kb_metadata.py
- [[TestMetadataFilters]] - code - backend/tests/test_kb_metadata.py
- [[TestProposeMetadata]] - code - backend/tests/test_kb_metadata.py
- [[Tests for metadata extraction & enrichment (Idea 13, phrases 22-30).]] - rationale - backend/tests/test_kb_metadata.py
- [[When AI is disabled, language is set by detect_language heuristic.]] - rationale - backend/tests/test_kb_metadata.py
- [[_make_doc()_14]] - code - backend/tests/test_kb_metadata.py
- [[_provenance_ai()]] - code - backend/app/services/kb/metadata.py
- [[_signup()_59]] - code - backend/tests/test_kb_metadata.py
- [[apply_metadata_update()]] - code - backend/app/services/kb/metadata.py
- [[date_9]] - code
- [[detect_language()]] - code - backend/app/services/kb/metadata.py
- [[enrich_metadata()]] - code - backend/app/services/kb/metadata.py
- [[estimate_reading_time()]] - code - backend/app/services/kb/metadata.py
- [[extract_frontmatter()]] - code - backend/app/services/kb/metadata.py
- [[metadata.py]] - code - backend/app/services/kb/metadata.py
- [[metadata_filters with author matches case-insensitively.]] - rationale - backend/tests/test_kb_metadata.py
- [[metadata_filters with date_from and date_to.]] - rationale - backend/tests/test_kb_metadata.py
- [[metadata_filters with language exact match.]] - rationale - backend/tests/test_kb_metadata.py
- [[metadata_filters with no filters returns the original query unchanged.]] - rationale - backend/tests/test_kb_metadata.py
- [[metadata_filters()]] - code - backend/app/services/kb/metadata.py
- [[propose_metadata()]] - code - backend/app/services/kb/metadata.py
- [[test_kb_metadata.py]] - code - backend/tests/test_kb_metadata.py
- [[update.metadata dict is merged into metadata_json.]] - rationale - backend/tests/test_kb_metadata.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_19
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Community 5]]
- 7 edges to [[_COMMUNITY_Community 2]]
- 6 edges to [[_COMMUNITY_Community 1]]
- 6 edges to [[_COMMUNITY_Community 21]]
- 5 edges to [[_COMMUNITY_Community 64]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 43]]
- 2 edges to [[_COMMUNITY_Community 109]]
- 2 edges to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 92]]

## Top bridge nodes
- [[metadata.py]] - degree 23, connects to 7 communities
- [[test_kb_metadata.py]] - degree 26, connects to 5 communities
- [[propose_metadata()]] - degree 15, connects to 4 communities
- [[apply_metadata_update()]] - degree 13, connects to 4 communities
- [[KbMetadataUpdate_1]] - degree 16, connects to 2 communities