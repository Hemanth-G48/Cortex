---
type: community
cohesion: 0.07
members: 55
---

# Community 37

**Cohesion:** 0.07 - loosely connected
**Members:** 55 nodes

## Members
- [[.test_aliases_merge_on_reuse()]] - code - backend/tests/test_kb_concepts.py
- [[.test_collapses_whitespace()]] - code - backend/tests/test_kb_concepts.py
- [[.test_concept_404_for_other_user()]] - code - backend/tests/test_kb_concepts.py
- [[.test_dedupes_existing_edge()]] - code - backend/tests/test_kb_concepts.py
- [[.test_definition_only_updated_when_empty()]] - code - backend/tests/test_kb_concepts.py
- [[.test_deterministic_with_ai_disabled()]] - code - backend/tests/test_kb_concepts.py
- [[.test_empty_returns_empty()]] - code - backend/tests/test_kb_concepts.py
- [[.test_get_concepts_returns_only_owned()]] - code - backend/tests/test_kb_concepts.py
- [[.test_lowercase_and_trim()]] - code - backend/tests/test_kb_concepts.py
- [[.test_mentions_edge_created()]] - code - backend/tests/test_kb_concepts.py
- [[.test_pagination_shape()]] - code - backend/tests/test_kb_concepts.py
- [[.test_persists_concepts_before_linking_mentions()]] - code - backend/tests/test_kb_concepts.py
- [[.test_same_name_creates_one_row()]] - code - backend/tests/test_kb_concepts.py
- [[.test_singularization()]] - code - backend/tests/test_kb_concepts.py
- [[.test_strips_trailing_punctuation()]] - code - backend/tests/test_kb_concepts.py
- [[.test_user_b_concepts_invisible_to_user_a()]] - code - backend/tests/test_kb_concepts.py
- [[.test_weight_clamped_to_minimum()]] - code - backend/tests/test_kb_concepts.py
- [[Build MENTIONS edges for each concept found in the document text (phrase 46).]] - rationale - backend/app/services/kb/concepts.py
- [[Compute IDF scores across a corpus of token lists.]] - rationale - backend/app/services/kb/concepts.py
- [[Concept extraction & canonicalization services (Phase 2, Idea 15, phrases 43-47)]] - rationale - backend/app/services/kb/concepts.py
- [[Deterministic TF-IDF noun-phrase extraction (phrase 44).      Builds a per-user]] - rationale - backend/app/services/kb/concepts.py
- [[Extract concepts for a document (phrase 43).      If AI is available and the dai]] - rationale - backend/app/services/kb/concepts.py
- [[Find existing concept or create one (phrase 47).      Match is by (user_id, cano]] - rationale - backend/app/services/kb/concepts.py
- [[Idea 15 — concept extraction & canonicalization tests (phrase 48).  Covers cano]] - rationale - backend/tests/test_kb_concepts.py
- [[KbConcept_1]] - code
- [[KbConcept model — canonical concepts (Phase 2, Idea 15).  One canonical row per]] - rationale - backend/app/models/kb/concept.py
- [[KbDocument_13]] - code
- [[Normalize a raw concept name to its canonical form (phrase 45).      Steps lowe]] - rationale - backend/app/services/kb/concepts.py
- [[Orchestrate concept extraction for a single document (entry point).      Extract]] - rationale - backend/app/services/kb/concepts.py
- [[Regression extract_for_document used to hand unpersisted concept         object]] - rationale - backend/tests/test_kb_concepts.py
- [[Session_141]] - code
- [[Split text into lowercase word tokens.]] - rationale - backend/app/services/kb/concepts.py
- [[TestCanonicalize]] - code - backend/tests/test_kb_concepts.py
- [[TestCreateOrReuse]] - code - backend/tests/test_kb_concepts.py
- [[TestExtractForDocument]] - code - backend/tests/test_kb_concepts.py
- [[TestMentionsEdge]] - code - backend/tests/test_kb_concepts.py
- [[TestPerUserIsolation_1]] - code - backend/tests/test_kb_concepts.py
- [[TestTfidfConcepts]] - code - backend/tests/test_kb_concepts.py
- [[Very rare mentions still get weight = 0.05.]] - rationale - backend/tests/test_kb_concepts.py
- [[With AI_ENABLED=False, extract_concepts must use TF-IDF.]] - rationale - backend/tests/test_kb_concepts.py
- [[_add_chunk()_1]] - code - backend/tests/test_kb_concepts.py
- [[_add_doc()]] - code - backend/tests/test_kb_concepts.py
- [[_idf_scores()]] - code - backend/app/services/kb/concepts.py
- [[_make_engine()]] - code - backend/tests/test_kb_concepts.py
- [[_signup()_28]] - code - backend/tests/test_kb_concepts.py
- [[_tokenize()]] - code - backend/app/services/kb/concepts.py
- [[canonicalize()]] - code - backend/app/services/kb/concepts.py
- [[concept.py]] - code - backend/app/models/kb/concept.py
- [[concepts.py]] - code - backend/app/services/kb/concepts.py
- [[create_or_reuse()]] - code - backend/app/services/kb/concepts.py
- [[extract_concepts()]] - code - backend/app/services/kb/concepts.py
- [[extract_for_document()_1]] - code - backend/app/services/kb/concepts.py
- [[link_mentions()]] - code - backend/app/services/kb/concepts.py
- [[test_kb_concepts.py]] - code - backend/tests/test_kb_concepts.py
- [[tfidf_concepts()]] - code - backend/app/services/kb/concepts.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_37
SORT file.name ASC
```

## Connections to other communities
- 18 edges to [[_COMMUNITY_Community 5]]
- 16 edges to [[_COMMUNITY_Community 2]]
- 14 edges to [[_COMMUNITY_Community 29]]
- 7 edges to [[_COMMUNITY_Community 54]]
- 5 edges to [[_COMMUNITY_Community 1]]
- 5 edges to [[_COMMUNITY_Community 16]]
- 4 edges to [[_COMMUNITY_Community 64]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 20]]
- 2 edges to [[_COMMUNITY_Community 127]]
- 2 edges to [[_COMMUNITY_Community 12]]
- 2 edges to [[_COMMUNITY_Community 177]]
- 1 edge to [[_COMMUNITY_Community 38]]
- 1 edge to [[_COMMUNITY_Community 17]]

## Top bridge nodes
- [[concepts.py]] - degree 27, connects to 10 communities
- [[test_kb_concepts.py]] - degree 27, connects to 6 communities
- [[extract_concepts()]] - degree 16, connects to 5 communities
- [[create_or_reuse()]] - degree 14, connects to 5 communities
- [[extract_for_document()_1]] - degree 12, connects to 3 communities