---
source_file: "backend/app/services/vector_store.py"
type: "code"
community: "Community 39"
location: "L27"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_39
---

# VectorStore

## Connections
- [[.__init__()_11]] - `method` [EXTRACTED]
- [[.__len__()]] - `method` [EXTRACTED]
- [[.add()]] - `method` [EXTRACTED]
- [[.clear()_1]] - `method` [EXTRACTED]
- [[.delete()]] - `method` [EXTRACTED]
- [[.query()]] - `method` [EXTRACTED]
- [[FileVectorStore]] - `uses` [INFERRED]
- [[Simple in-memory dense-vector store with cosine retrieval.]] - `rationale_for` [EXTRACTED]
- [[TestEmbedDocumentChunks]] - `uses` [INFERRED]
- [[TestFileVectorStorePersistence]] - `uses` [INFERRED]
- [[TestStats]] - `uses` [INFERRED]
- [[TestSyncIndex]] - `uses` [INFERRED]
- [[get_pg_store()]] - `references` [EXTRACTED]
- [[get_store()]] - `references` [EXTRACTED]
- [[test_add_and_query_nearest_neighbour()]] - `calls` [EXTRACTED]
- [[test_add_mismatched_lengths_raises()]] - `calls` [EXTRACTED]
- [[test_clear_empties_store()]] - `calls` [EXTRACTED]
- [[test_delete_missing_id_is_noop()]] - `calls` [EXTRACTED]
- [[test_delete_removes_vectors()]] - `calls` [EXTRACTED]
- [[test_dimension_mismatch_returns_empty()]] - `calls` [EXTRACTED]
- [[test_empty_store_returns_empty()]] - `calls` [EXTRACTED]
- [[test_query_returns_top_k_sorted()]] - `calls` [EXTRACTED]
- [[test_replace_same_id_keeps_single_row()]] - `calls` [EXTRACTED]
- [[test_vector_persistence.py]] - `imports` [EXTRACTED]
- [[test_vector_store.py]] - `imports` [EXTRACTED]
- [[test_zero_query_vector_returns_empty()]] - `calls` [EXTRACTED]
- [[vector_store.py]] - `contains` [EXTRACTED]
- [[vector_store_file.py]] - `imports` [EXTRACTED]
- [[vector_store_pg.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_39