---
type: community
cohesion: 0.06
members: 91
---

# Community 13

**Cohesion:** 0.06 - loosely connected
**Members:** 91 nodes

## Members
- [[.test_backlinks_false_omits_reverse()]] - code - backend/tests/test_kb_graph.py
- [[.test_below_threshold_not_created()]] - code - backend/tests/test_kb_graph.py
- [[.test_below_threshold_returns_none()]] - code - backend/tests/test_kb_graph.py
- [[.test_concept_filter()]] - code - backend/tests/test_kb_graph.py
- [[.test_creates_mentions_edges()]] - code - backend/tests/test_kb_graph.py
- [[.test_creates_wikilink_and_backlink()]] - code - backend/tests/test_kb_graph.py
- [[.test_dedupe_same_key()]] - code - backend/tests/test_kb_graph.py
- [[.test_edge_source_target_format()]] - code - backend/tests/test_kb_graph.py
- [[.test_filters_by_min_weight()]] - code - backend/tests/test_kb_graph.py
- [[.test_idempotent()_1]] - code - backend/tests/test_kb_graph.py
- [[.test_insert_new_edge()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_extracted_text_returns_empty()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_matching_concepts()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_mentions_no_edges()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_overwrite_returns_existing()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_target_returns_none()]] - code - backend/tests/test_kb_graph.py
- [[.test_no_truncation_when_under_limit()]] - code - backend/tests/test_kb_graph.py
- [[.test_node_id_format()]] - code - backend/tests/test_kb_graph.py
- [[.test_ordered_by_weight_desc()]] - code - backend/tests/test_kb_graph.py
- [[.test_outbound_and_inbound()]] - code - backend/tests/test_kb_graph.py
- [[.test_overwrite_updates_weight_and_provenance()]] - code - backend/tests/test_kb_graph.py
- [[.test_per_user_isolation()_4]] - code - backend/tests/test_kb_graph.py
- [[.test_per_user_isolation()_5]] - code - backend/tests/test_kb_graph.py
- [[.test_relation_filter()_1]] - code - backend/tests/test_kb_graph.py
- [[.test_relation_filter()]] - code - backend/tests/test_kb_graph.py
- [[.test_resolves_by_path_rel()]] - code - backend/tests/test_kb_graph.py
- [[.test_resolves_by_title_fallback()]] - code - backend/tests/test_kb_graph.py
- [[.test_returns_doc_targets()]] - code - backend/tests/test_kb_graph.py
- [[.test_returns_mention_concepts()]] - code - backend/tests/test_kb_graph.py
- [[.test_self_link_skipped()]] - code - backend/tests/test_kb_graph.py
- [[.test_shares_concept_edge()]] - code - backend/tests/test_kb_graph.py
- [[.test_source_filter()]] - code - backend/tests/test_kb_graph.py
- [[.test_tag_filter()]] - code - backend/tests/test_kb_graph.py
- [[.test_total_counts()]] - code - backend/tests/test_kb_graph.py
- [[.test_truncation_flag()]] - code - backend/tests/test_kb_graph.py
- [[.test_weight_filtering()]] - code - backend/tests/test_kb_graph.py
- [[.test_weight_is_relative_frequency()]] - code - backend/tests/test_kb_graph.py
- [[Add ``SHARES_CONCEPT`` edges between documents that co-occur in chunks.      Fin]] - rationale - backend/app/services/kb/graph.py
- [[Aggregated sidebar data concepts + related notes (phrase 64).]] - rationale - backend/app/routers/kb_edges.py
- [[BaseModel_12]] - code
- [[Build a graph response with nodes and edges for ``user_id``.      Filters]] - rationale - backend/app/services/kb/graph.py
- [[Create ``MENTIONS`` edges from ``doc`` to ``KbConcept`` rows.      Scans ``doc.e]] - rationale - backend/app/services/kb/graph.py
- [[Create a manual edge (phrase 62). Rejects self-edges  bad targets.]] - rationale - backend/app/routers/kb_edges.py
- [[Delete any edge the user owns — manual or auto-inferred (phrase 63).]] - rationale - backend/app/routers/kb_edges.py
- [[EdgeCreate]] - code - backend/app/routers/kb_edges.py
- [[Idea 16, Group 6 (phrases 51-60) — knowledge graph nodes & edges tests.]] - rationale - backend/tests/test_kb_graph.py
- [[KbDocument_17]] - code
- [[KbDocument_45]] - code
- [[KbGraphEdge]] - code - backend/app/schemas/kb.py
- [[KbGraphNode]] - code - backend/app/schemas/kb.py
- [[KbGraphResponse_2]] - code
- [[Knowledge-graph helpers (Idea 16, phrases 51-58).  Every function is user-scoped]] - rationale - backend/app/services/kb/graph.py
- [[Manual concept linking + document links panel (Phase 4, Idea 37).  - ``POST api]] - rationale - backend/app/routers/kb_edges.py
- [[Return MENTIONS concept targets for ``doc_id``.      Each entry has ``concept_id]] - rationale - backend/app/services/kb/graph.py
- [[Return both inbound and outbound edges for ``doc_id`` as dicts.      Each dict h]] - rationale - backend/app/services/kb/graph.py
- [[Return document targets of edges for ``doc_id``.      Each entry has ``id``, ``t]] - rationale - backend/app/services/kb/graph.py
- [[Scan ``doc.extracted_text`` and frontmatter tags for wikilinks.      For each li]] - rationale - backend/app/services/kb/graph.py
- [[Session_41]] - code
- [[Session_159]] - code
- [[Strip leading ``.`` and trailing ``.md`` for wikilink resolution.]] - rationale - backend/app/services/kb/graph.py
- [[TestAddEdge]] - code - backend/tests/test_kb_graph.py
- [[TestBuildGraph]] - code - backend/tests/test_kb_graph.py
- [[TestBuildWikilinkEdges]] - code - backend/tests/test_kb_graph.py
- [[TestConceptsOf]] - code - backend/tests/test_kb_graph.py
- [[TestCooccurrenceEdges]] - code - backend/tests/test_kb_graph.py
- [[TestLinkMentionsEdges]] - code - backend/tests/test_kb_graph.py
- [[TestNeighbors]] - code - backend/tests/test_kb_graph.py
- [[TestRelatedDocs]] - code - backend/tests/test_kb_graph.py
- [[Try to match a wikilink target to a ``KbDocument``.      First compares normalis]] - rationale - backend/app/services/kb/graph.py
- [[Upsert a ``KbEdge`` for ``user_id``.      Dedupe key ``(user_id, source_documen]] - rationale - backend/app/services/kb/graph.py
- [[User_26]] - code
- [[_doc()_2]] - code - backend/tests/test_kb_graph.py
- [[_normalise_path()]] - code - backend/app/services/kb/graph.py
- [[_resolve_document_by_path()]] - code - backend/app/services/kb/graph.py
- [[_user()_1]] - code - backend/tests/test_kb_graph.py
- [[add_edge()]] - code - backend/app/services/kb/graph.py
- [[build_graph()]] - code - backend/app/services/kb/graph.py
- [[build_wikilink_edges()]] - code - backend/app/services/kb/graph.py
- [[concepts_of()]] - code - backend/app/services/kb/graph.py
- [[cooccurrence_edges()]] - code - backend/app/services/kb/graph.py
- [[create_edge()]] - code - backend/app/routers/kb_edges.py
- [[delete_edge()]] - code - backend/app/routers/kb_edges.py
- [[document_links()]] - code - backend/app/routers/kb_edges.py
- [[graph.py]] - code - backend/app/services/kb/graph.py
- [[graph_engine()]] - code - backend/tests/test_kb_graph.py
- [[graph_session()]] - code - backend/tests/test_kb_graph.py
- [[kb_edges.py]] - code - backend/app/routers/kb_edges.py
- [[link_mentions_edges()]] - code - backend/app/services/kb/graph.py
- [[neighbors()]] - code - backend/app/services/kb/graph.py
- [[related_docs()]] - code - backend/app/services/kb/graph.py
- [[test_kb_graph.py]] - code - backend/tests/test_kb_graph.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_13
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_Community 54]]
- 18 edges to [[_COMMUNITY_Community 29]]
- 17 edges to [[_COMMUNITY_Community 5]]
- 12 edges to [[_COMMUNITY_Community 2]]
- 9 edges to [[_COMMUNITY_Community 21]]
- 6 edges to [[_COMMUNITY_Community 250]]
- 5 edges to [[_COMMUNITY_Community 127]]
- 5 edges to [[_COMMUNITY_Community 62]]
- 4 edges to [[_COMMUNITY_Community 92]]
- 4 edges to [[_COMMUNITY_Community 43]]
- 4 edges to [[_COMMUNITY_Community 265]]
- 4 edges to [[_COMMUNITY_Community 171]]
- 3 edges to [[_COMMUNITY_Community 1]]
- 3 edges to [[_COMMUNITY_Community 10]]
- 3 edges to [[_COMMUNITY_Community 70]]
- 3 edges to [[_COMMUNITY_Community 99]]
- 2 edges to [[_COMMUNITY_Community 325]]
- 2 edges to [[_COMMUNITY_Community 64]]
- 2 edges to [[_COMMUNITY_Community 179]]
- 2 edges to [[_COMMUNITY_Community 17]]
- 2 edges to [[_COMMUNITY_Community 296]]

## Top bridge nodes
- [[graph.py]] - degree 39, connects to 16 communities
- [[test_kb_graph.py]] - degree 37, connects to 9 communities
- [[build_graph()]] - degree 28, connects to 9 communities
- [[add_edge()]] - degree 51, connects to 8 communities
- [[kb_edges.py]] - degree 23, connects to 6 communities