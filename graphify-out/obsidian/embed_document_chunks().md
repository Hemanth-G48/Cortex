---
source_file: "backend/app/services/kb/embedder.py"
type: "code"
community: "Community 2"
location: "L28"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_2
---

# embed_document_chunks()

## Connections
- [[.json_dumps()]] - `calls` [EXTRACTED]
- [[.test_embeds_chunks_and_writes_rows()]] - `calls` [EXTRACTED]
- [[.test_empty_doc_has_no_embeddings()]] - `calls` [EXTRACTED]
- [[.test_idempotent_rerun_skips_already_embedded()]] - `calls` [EXTRACTED]
- [[.test_stats_returns_correct_counts()]] - `calls` [EXTRACTED]
- [[.test_sync_index_is_idempotent()]] - `calls` [EXTRACTED]
- [[.test_sync_index_rebuilds_store()]] - `calls` [EXTRACTED]
- [[Embed all un-embedded chunks of a document in a single transaction.      Skips c]] - `rationale_for` [EXTRACTED]
- [[KbChunk]] - `indirect_call` [INFERRED]
- [[KbDocument]] - `indirect_call` [INFERRED]
- [[KbEmbedding]] - `calls` [EXTRACTED]
- [[Session_148]] - `references` [EXTRACTED]
- [[_embed()]] - `calls` [EXTRACTED]
- [[backend_embed()]] - `calls` [EXTRACTED]
- [[embedder.py]] - `contains` [EXTRACTED]
- [[embedding_hash()]] - `calls` [EXTRACTED]
- [[reindex.py]] - `imports` [EXTRACTED]
- [[run_document_stages()]] - `calls` [EXTRACTED]
- [[test_kb_migration.py]] - `imports` [EXTRACTED]
- [[test_vector_persistence.py]] - `imports` [EXTRACTED]
- [[utcnow()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_2