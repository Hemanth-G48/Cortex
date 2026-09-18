---
type: community
cohesion: 0.09
members: 52
---

# Community 45

**Cohesion:** 0.09 - loosely connected
**Members:** 52 nodes

## Members
- [[.test_archive_document_sets_status()]] - code - backend/tests/test_kb_neardup.py
- [[.test_archive_endpoint()]] - code - backend/tests/test_kb_neardup.py
- [[.test_archive_nonexistent_doc_returns_404()]] - code - backend/tests/test_kb_neardup.py
- [[.test_candidate_pairs_returns_empty_for_new_user()]] - code - backend/tests/test_kb_neardup.py
- [[.test_candidate_pairs_skips_same_document()]] - code - backend/tests/test_kb_neardup.py
- [[.test_close_paraphrase_flagged()]] - code - backend/tests/test_kb_neardup.py
- [[.test_different_texts_not_flagged()]] - code - backend/tests/test_kb_neardup.py
- [[.test_get_duplicates_endpoint()]] - code - backend/tests/test_kb_neardup.py
- [[.test_identical_chunks_flagged()]] - code - backend/tests/test_kb_neardup.py
- [[.test_list_duplicates()]] - code - backend/tests/test_kb_neardup.py
- [[.test_merge_documents_reassigns_chunks()]] - code - backend/tests/test_kb_neardup.py
- [[.test_merge_endpoint()]] - code - backend/tests/test_kb_neardup.py
- [[.test_per_user_isolation()_7]] - code - backend/tests/test_kb_neardup.py
- [[.test_scan_endpoint()]] - code - backend/tests/test_kb_neardup.py
- [[All ``DUPLICATE_OF`` doc pairs already recorded for user_id.      One query in]] - rationale - backend/app/services/kb/neardup.py
- [[Archive a duplicate document by setting its status to ``archived``.      Retur]] - rationale - backend/app/services/kb/neardup.py
- [[Cosine similarity between two vectors (numpy).]] - rationale - backend/app/services/kb/neardup.py
- [[Create KbEmbedding rows for every chunk of doc_id using local_embed.]] - rationale - backend/tests/test_kb_neardup.py
- [[Create a document + chunk directly in the DB.      The upload endpoint content-d]] - rationale - backend/tests/test_kb_neardup.py
- [[Decode vector and padtruncate it to dim; None when empty.]] - rationale - backend/app/services/kb/neardup.py
- [[Decode a JSON-encoded embedding vector stored in ``kb_embeddings``.]] - rationale - backend/app/services/kb/neardup.py
- [[Deterministic, content-derived vectors — never raises, never hits network.]] - rationale - backend/app/services/embeddings.py
- [[Exact max chunk-pair cosine between two documents (vectorized).      Returns ``(]] - rationale - backend/app/services/kb/neardup.py
- [[Mean of a document's chunk vectors (padtruncate to dim).]] - rationale - backend/app/services/kb/neardup.py
- [[Merge duplicate documents into keep_id.      Reassigns all per-user references]] - rationale - backend/app/services/kb/neardup.py
- [[Near-duplicate detection service (Phase 2, Idea 19, phrases 82-86).  Cosine-simi]] - rationale - backend/app/services/kb/neardup.py
- [[Near-duplicate detection tests (Phase 2, Idea 19, phrase 87).  Tests candidate g]] - rationale - backend/tests/test_kb_neardup.py
- [[Return True if a DUPLICATE_OF edge already links these two docs.]] - rationale - backend/app/services/kb/neardup.py
- [[Return all ``DUPLICATE_OF`` edges for user_id as KbDuplicateItem dicts.      `]] - rationale - backend/app/services/kb/neardup.py
- [[Return candidate near-duplicate embedding pairs for user_id.      method def]] - rationale - backend/app/services/kb/neardup.py
- [[Scan and record near-duplicate document pairs for user_id.      For each quali]] - rationale - backend/app/services/kb/neardup.py
- [[Session_173]] - code
- [[TestScanDuplicates]] - code - backend/tests/test_kb_neardup.py
- [[_add_embeddings()]] - code - backend/tests/test_kb_neardup.py
- [[_decoded_vector()]] - code - backend/app/services/kb/neardup.py
- [[_existing_dup_keys()]] - code - backend/app/services/kb/neardup.py
- [[_max_chunk_sim()]] - code - backend/app/services/kb/neardup.py
- [[_normalized_vec()]] - code - backend/app/services/kb/neardup.py
- [[_pooled_vector()]] - code - backend/app/services/kb/neardup.py
- [[_signup()_65]] - code - backend/tests/test_kb_neardup.py
- [[_skip_existing_duplicate()]] - code - backend/app/services/kb/neardup.py
- [[_upload_doc()]] - code - backend/tests/test_kb_neardup.py
- [[archive_document()]] - code - backend/app/services/kb/neardup.py
- [[candidate_pairs()]] - code - backend/app/services/kb/neardup.py
- [[cosine_sim()]] - code - backend/app/services/kb/neardup.py
- [[list_duplicates()]] - code - backend/app/services/kb/neardup.py
- [[local_embed()]] - code - backend/app/services/embeddings.py
- [[merge_documents()]] - code - backend/app/services/kb/neardup.py
- [[ndarray]] - code
- [[neardup.py]] - code - backend/app/services/kb/neardup.py
- [[scan_duplicates()]] - code - backend/app/services/kb/neardup.py
- [[test_kb_neardup.py]] - code - backend/tests/test_kb_neardup.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_45
SORT file.name ASC
```

## Connections to other communities
- 28 edges to [[_COMMUNITY_Community 2]]
- 21 edges to [[_COMMUNITY_Community 5]]
- 6 edges to [[_COMMUNITY_Community 54]]
- 5 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 21]]
- 3 edges to [[_COMMUNITY_Community 248]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 92]]
- 2 edges to [[_COMMUNITY_Community 28]]
- 2 edges to [[_COMMUNITY_Community 62]]
- 2 edges to [[_COMMUNITY_Community 279]]
- 2 edges to [[_COMMUNITY_Community 16]]
- 1 edge to [[_COMMUNITY_Community 116]]
- 1 edge to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 176]]
- 1 edge to [[_COMMUNITY_Community 17]]

## Top bridge nodes
- [[neardup.py]] - degree 31, connects to 8 communities
- [[merge_documents()]] - degree 13, connects to 7 communities
- [[scan_duplicates()]] - degree 19, connects to 6 communities
- [[test_kb_neardup.py]] - degree 21, connects to 5 communities
- [[archive_document()]] - degree 10, connects to 5 communities