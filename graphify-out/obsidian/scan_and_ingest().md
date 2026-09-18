---
source_file: "backend/app/services/kb/scanner.py"
type: "code"
community: "Community 22"
location: "L275"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_22
---

# scan_and_ingest()

## Connections
- [[.test_daily_life_outside_notes_root_is_not_scanned()]] - `calls` [EXTRACTED]
- [[.test_deleted_file_swept()]] - `calls` [EXTRACTED]
- [[.test_duplicate_filenames_in_different_folders_are_separate()]] - `calls` [EXTRACTED]
- [[.test_failure_does_not_block_others_and_is_retryable()]] - `calls` [EXTRACTED]
- [[.test_full_migration_causes_zero_reembedding()]] - `calls` [EXTRACTED]
- [[.test_genuine_duplicate_still_dedupes()]] - `calls` [EXTRACTED]
- [[.test_modified_file_replaces_stale_embeddings()]] - `calls` [EXTRACTED]
- [[.test_move_within_scan_order_is_idempotent()]] - `calls` [EXTRACTED]
- [[.test_new_file_embeds()]] - `calls` [EXTRACTED]
- [[.test_path_only_move_reuses_document_chunks_and_embeddings()]] - `calls` [EXTRACTED]
- [[.test_purge_removes_source_and_all_index_rows()]] - `calls` [EXTRACTED]
- [[.test_resync_no_changes_is_all_unchanged()]] - `calls` [EXTRACTED]
- [[.test_scanner_skips_root_level_daily_life_folder()]] - `calls` [EXTRACTED]
- [[KbDocument]] - `indirect_call` [INFERRED]
- [[KbSource]] - `indirect_call` [INFERRED]
- [[Scan a source (optionally one folder inside it), then run the ingest     pipelin]] - `rationale_for` [EXTRACTED]
- [[Session_193]] - `references` [EXTRACTED]
- [[_like_escape()_1]] - `calls` [EXTRACTED]
- [[_local_sync()]] - `calls` [EXTRACTED]
- [[_poll_once()]] - `calls` [EXTRACTED]
- [[_run_inline()]] - `calls` [EXTRACTED]
- [[auto_sync.py]] - `imports` [EXTRACTED]
- [[ensure_fts_schema_for()]] - `calls` [EXTRACTED]
- [[ingest_document()]] - `calls` [EXTRACTED]
- [[jobs.py]] - `imports` [EXTRACTED]
- [[migrate.py]] - `imports` [EXTRACTED]
- [[run_migration()]] - `calls` [EXTRACTED]
- [[scan_source()_1]] - `calls` [EXTRACTED]
- [[scanner.py]] - `contains` [EXTRACTED]
- [[test_kb_migration.py]] - `imports` [EXTRACTED]
- [[watcher.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_22