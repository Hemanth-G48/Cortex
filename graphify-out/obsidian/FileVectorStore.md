---
source_file: "backend/app/services/vector_store_file.py"
type: "code"
community: "Community 39"
location: "L27"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_39
---

# FileVectorStore

## Connections
- [[.__init__()_12]] - `method` [EXTRACTED]
- [[.__len__()_1]] - `method` [EXTRACTED]
- [[._load()_1]] - `method` [EXTRACTED]
- [[.add()_1]] - `method` [EXTRACTED]
- [[.clear()_2]] - `method` [EXTRACTED]
- [[.delete()_1]] - `method` [EXTRACTED]
- [[.save()]] - `method` [EXTRACTED]
- [[.test_add_replace_and_delete_persist()]] - `calls` [EXTRACTED]
- [[.test_corrupt_files_fallback_to_empty()]] - `calls` [EXTRACTED]
- [[.test_fresh_store_with_no_files_is_empty()]] - `calls` [EXTRACTED]
- [[.test_save_and_load_survives_restart()]] - `calls` [EXTRACTED]
- [[.test_sync_index_is_idempotent()]] - `calls` [EXTRACTED]
- [[.test_sync_index_rebuilds_store()]] - `calls` [EXTRACTED]
- [[File-backed vector store that persists to disk.      Mirrors the in-memory ``Vec]] - `rationale_for` [EXTRACTED]
- [[TestEmbedDocumentChunks]] - `uses` [INFERRED]
- [[TestFileVectorStorePersistence]] - `uses` [INFERRED]
- [[TestStats]] - `uses` [INFERRED]
- [[TestSyncIndex]] - `uses` [INFERRED]
- [[VectorStore]] - `uses` [INFERRED]
- [[get_file_store()]] - `references` [EXTRACTED]
- [[test_vector_persistence.py]] - `imports` [EXTRACTED]
- [[vector_store_file.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_39