---
source_file: "backend/app/services/kb/embedder.py"
type: "code"
community: "Community 2"
location: "L231"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_2
---

# sync_index()

## Connections
- [[.json_loads()]] - `calls` [EXTRACTED]
- [[.test_sync_index_is_idempotent()]] - `calls` [EXTRACTED]
- [[.test_sync_index_rebuilds_store()]] - `calls` [EXTRACTED]
- [[KbEmbedding]] - `indirect_call` [INFERRED]
- [[Rebuild the active vector store from kb_embeddings rows for a user.      Idempot]] - `rationale_for` [EXTRACTED]
- [[Session_148]] - `references` [EXTRACTED]
- [[embedder.py]] - `contains` [EXTRACTED]
- [[get_store()]] - `calls` [EXTRACTED]
- [[reindex.py]] - `imports` [EXTRACTED]
- [[reindex_documents()]] - `calls` [EXTRACTED]
- [[test_vector_persistence.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_2