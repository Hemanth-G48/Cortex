---
type: community
cohesion: 0.06
members: 55
---

# Community 39

**Cohesion:** 0.06 - loosely connected
**Members:** 55 nodes

## Members
- [[.__init__()_12]] - code - backend/app/services/vector_store_file.py
- [[.__init__()_11]] - code - backend/app/services/vector_store.py
- [[.__len__()_1]] - code - backend/app/services/vector_store_file.py
- [[.__len__()]] - code - backend/app/services/vector_store.py
- [[._load()_1]] - code - backend/app/services/vector_store_file.py
- [[.add()_1]] - code - backend/app/services/vector_store_file.py
- [[.add()]] - code - backend/app/services/vector_store.py
- [[.clear()_2]] - code - backend/app/services/vector_store_file.py
- [[.clear()_1]] - code - backend/app/services/vector_store.py
- [[.delete()_1]] - code - backend/app/services/vector_store_file.py
- [[.delete()]] - code - backend/app/services/vector_store.py
- [[.query()]] - code - backend/app/services/vector_store.py
- [[.save()]] - code - backend/app/services/vector_store_file.py
- [[.test_add_replace_and_delete_persist()]] - code - backend/tests/test_vector_persistence.py
- [[.test_corrupt_files_fallback_to_empty()]] - code - backend/tests/test_vector_persistence.py
- [[.test_fresh_store_with_no_files_is_empty()]] - code - backend/tests/test_vector_persistence.py
- [[.test_save_and_load_survives_restart()]] - code - backend/tests/test_vector_persistence.py
- [[A store with no existing files starts empty.]] - rationale - backend/tests/test_vector_persistence.py
- [[Add vectors for the given ids, replacing any existing id.]] - rationale - backend/app/services/vector_store.py
- [[Add, replace, delete — all persisted across restarts.]] - rationale - backend/tests/test_vector_persistence.py
- [[Corrupt .npy or ids.json is ignored; store starts empty.]] - rationale - backend/tests/test_vector_persistence.py
- [[File-backed vector store (Second Brain Phase 2, Idea 12, phrase 14).  Persists t]] - rationale - backend/app/services/vector_store_file.py
- [[File-backed vector store that persists to disk.      Mirrors the in-memory ``Vec]] - rationale - backend/app/services/vector_store_file.py
- [[FileVectorStore]] - code - backend/app/services/vector_store_file.py
- [[In-memory vector store with cosine-similarity retrieval.  Zenith-Study-Planner G]] - rationale - backend/app/services/vector_store.py
- [[Load persisted state if present; silently ignore corruption.]] - rationale - backend/app/services/vector_store_file.py
- [[Remove vectors for the given ids (missing ids are ignored).]] - rationale - backend/app/services/vector_store.py
- [[Return a pgvector-backed store.      Raises ``ImportError`` when the ``pgvector`]] - rationale - backend/app/services/vector_store_pg.py
- [[Return the shared file-backed store singleton.]] - rationale - backend/app/services/vector_store_file.py
- [[Return the shared store instance (swap point for backends).      Supported ``VEC]] - rationale - backend/app/services/vector_store.py
- [[Return the top-k nearest ids with cosine similarity scores.          Result item]] - rationale - backend/app/services/vector_store.py
- [[Simple in-memory dense-vector store with cosine retrieval.]] - rationale - backend/app/services/vector_store.py
- [[TestFileVectorStorePersistence]] - code - backend/tests/test_vector_persistence.py
- [[Tests for the vector store (Zenith-Study-Planner G1, Phase 3).]] - rationale - backend/tests/test_vector_store.py
- [[VectorStore]] - code - backend/app/services/vector_store.py
- [[Write the current matrix + id list to disk.]] - rationale - backend/app/services/vector_store_file.py
- [[Write vectors via one store instance; a fresh instance loads them.]] - rationale - backend/tests/test_vector_persistence.py
- [[get_file_store()]] - code - backend/app/services/vector_store_file.py
- [[get_pg_store()]] - code - backend/app/services/vector_store_pg.py
- [[get_store()]] - code - backend/app/services/vector_store.py
- [[pgvector backend for the persistent vector store (Second Brain Phase 2, Idea 12,]] - rationale - backend/app/services/vector_store_pg.py
- [[test_add_and_query_nearest_neighbour()]] - code - backend/tests/test_vector_store.py
- [[test_add_mismatched_lengths_raises()]] - code - backend/tests/test_vector_store.py
- [[test_clear_empties_store()]] - code - backend/tests/test_vector_store.py
- [[test_delete_missing_id_is_noop()]] - code - backend/tests/test_vector_store.py
- [[test_delete_removes_vectors()]] - code - backend/tests/test_vector_store.py
- [[test_dimension_mismatch_returns_empty()]] - code - backend/tests/test_vector_store.py
- [[test_empty_store_returns_empty()]] - code - backend/tests/test_vector_store.py
- [[test_query_returns_top_k_sorted()]] - code - backend/tests/test_vector_store.py
- [[test_replace_same_id_keeps_single_row()]] - code - backend/tests/test_vector_store.py
- [[test_vector_store.py]] - code - backend/tests/test_vector_store.py
- [[test_zero_query_vector_returns_empty()]] - code - backend/tests/test_vector_store.py
- [[vector_store.py]] - code - backend/app/services/vector_store.py
- [[vector_store_file.py]] - code - backend/app/services/vector_store_file.py
- [[vector_store_pg.py]] - code - backend/app/services/vector_store_pg.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_39
SORT file.name ASC
```

## Connections to other communities
- 17 edges to [[_COMMUNITY_Community 2]]
- 3 edges to [[_COMMUNITY_Community 1]]
- 2 edges to [[_COMMUNITY_Community 16]]

## Top bridge nodes
- [[vector_store.py]] - degree 11, connects to 2 communities
- [[vector_store_file.py]] - degree 7, connects to 2 communities
- [[VectorStore]] - degree 29, connects to 1 community
- [[FileVectorStore]] - degree 22, connects to 1 community
- [[get_store()]] - degree 8, connects to 1 community