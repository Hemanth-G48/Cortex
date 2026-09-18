---
type: community
cohesion: 0.06
members: 77
---

# Community 22

**Cohesion:** 0.06 - loosely connected
**Members:** 77 nodes

## Members
- [[.test_auto_sync_run_excludes_local_sources()]] - code - backend/tests/test_kb_migration.py
- [[.test_copies_only_knowledge_deltas_and_never_reembeds()]] - code - backend/tests/test_kb_migration.py
- [[.test_cross_user_duplicate_sources_disabled_not_deleted()]] - code - backend/tests/test_kb_migration.py
- [[.test_daily_life_outside_notes_root_is_not_scanned()]] - code - backend/tests/test_kb_migration.py
- [[.test_deleted_file_swept()]] - code - backend/tests/test_kb_migration.py
- [[.test_disabled_interval_never_fires()]] - code - backend/tests/test_kb_migration.py
- [[.test_duplicate_filenames_in_different_folders_are_separate()]] - code - backend/tests/test_kb_migration.py
- [[.test_failure_does_not_block_others_and_is_retryable()]] - code - backend/tests/test_kb_migration.py
- [[.test_full_migration_causes_zero_reembedding()]] - code - backend/tests/test_kb_migration.py
- [[.test_genuine_duplicate_still_dedupes()]] - code - backend/tests/test_kb_migration.py
- [[.test_job_registered_with_dedicated_toggle()]] - code - backend/tests/test_kb_migration.py
- [[.test_job_runs_through_automation_gate_and_audits()]] - code - backend/tests/test_kb_migration.py
- [[.test_local_sync_requires_configured_source()]] - code - backend/tests/test_kb_migration.py
- [[.test_modified_file_replaces_stale_embeddings()]] - code - backend/tests/test_kb_migration.py
- [[.test_move_within_scan_order_is_idempotent()]] - code - backend/tests/test_kb_migration.py
- [[.test_new_file_embeds()]] - code - backend/tests/test_kb_migration.py
- [[.test_path_only_move_reuses_document_chunks_and_embeddings()]] - code - backend/tests/test_kb_migration.py
- [[.test_purge_detaches_linked_courses()]] - code - backend/tests/test_kb_migration.py
- [[.test_purge_removes_source_and_all_index_rows()]] - code - backend/tests/test_kb_migration.py
- [[.test_repoint_is_idempotent()]] - code - backend/tests/test_kb_migration.py
- [[.test_resync_no_changes_is_all_unchanged()]] - code - backend/tests/test_kb_migration.py
- [[.test_run_local_syncs_only_local_sources()]] - code - backend/tests/test_kb_migration.py
- [[.test_run_migration_dry_run_moves_nothing()]] - code - backend/tests/test_kb_migration.py
- [[.test_same_user_sources_not_disabled()]] - code - backend/tests/test_kb_migration.py
- [[.test_scanner_skips_root_level_daily_life_folder()]] - code - backend/tests/test_kb_migration.py
- [[.test_scheduled_local_sync_gated_by_own_toggle()]] - code - backend/tests/test_kb_migration.py
- [[.test_watcher_automation_pass_fires_on_interval()]] - code - backend/tests/test_kb_migration.py
- [[Backup → reorganize → repoint roots → disable cross-user duplicates → rescan.]] - rationale - backend/app/services/kb/migrate.py
- [[Disable duplicate sources from other users on the same vault root.      The wa]] - rationale - backend/app/services/kb/migrate.py
- [[Even when a source is rooted at the vault root (pre-migration         layout), a]] - rationale - backend/tests/test_kb_migration.py
- [[Full loop automation.run_one gates on the toggle, runs the job         inline (]] - rationale - backend/tests/test_kb_migration.py
- [[Hard-delete a source docschunksembeddingsedgesfolders gone,         other u]] - rationale - backend/tests/test_kb_migration.py
- [[KbDocument_47]] - code
- [[KbSource_4]] - code
- [[KbSource_12]] - code
- [[Move a note to another folder with identical content → same doc id,         same]] - rationale - backend/tests/test_kb_migration.py
- [[Move top-level folders into notes, repoint the source root → the         scan s]] - rationale - backend/tests/test_kb_migration.py
- [[Point every source rooted at the vault at ``vault_rootnotes``.]] - rationale - backend/app/services/kb/migrate.py
- [[Recompute ``file_path`` for the source's documents after a root move.      The s]] - rationale - backend/app/services/kb/migrate.py
- [[SQLite online backup of the app database; returns the backup path.]] - rationale - backend/app/services/kb/migrate.py
- [[Scan a source (optionally one folder inside it), then run the ingest     pipelin]] - rationale - backend/app/services/kb/scanner.py
- [[Second Brain migration tests — notes + daily-life separation.  The non-negotia]] - rationale - backend/tests/test_kb_migration.py
- [[Session_169]] - code
- [[Session_235]] - code
- [[TestDailyLife]] - code - backend/tests/test_kb_migration.py
- [[TestIncrementalSync]] - code - backend/tests/test_kb_migration.py
- [[TestLocalSync]] - code - backend/tests/test_kb_migration.py
- [[TestMigration]] - code - backend/tests/test_kb_migration.py
- [[TestMoveReusesEverything]] - code - backend/tests/test_kb_migration.py
- [[TestOneFailedEmbedding]] - code - backend/tests/test_kb_migration.py
- [[TestPurgeSource]] - code - backend/tests/test_kb_migration.py
- [[TestScheduledLocalSyncJob]] - code - backend/tests/test_kb_migration.py
- [[The dedicated ``auto_local_sync`` automation job (Copy Recent Notes on     a tim]] - rationale - backend/tests/test_kb_migration.py
- [[The gitdriveclip job must never double-sync a local vault — local         sour]] - rationale - backend/tests/test_kb_migration.py
- [[The watcher's periodic pass calls automation.run_all per user with an         en]] - rationale - backend/tests/test_kb_migration.py
- [[Timestamped tarball of the whole vault; returns the archive path.]] - rationale - backend/app/services/kb/migrate.py
- [[Two files with identical content that BOTH exist are duplicates,         not mov]] - rationale - backend/tests/test_kb_migration.py
- [[Two sources on the same vault from different users the later one         is dis]] - rationale - backend/tests/test_kb_migration.py
- [[Walking order must not matter a second scan after the move still         report]] - rationale - backend/tests/test_kb_migration.py
- [[With the source rooted at ``notes`` (post-migration layout), a         sibling]] - rationale - backend/tests/test_kb_migration.py
- [[_chunk_ids()]] - code - backend/tests/test_kb_migration.py
- [[_doc_by_path()]] - code - backend/tests/test_kb_migration.py
- [[_embed()]] - code - backend/tests/test_kb_migration.py
- [[_embedding_count()]] - code - backend/tests/test_kb_migration.py
- [[_make_source()_4]] - code - backend/tests/test_kb_migration.py
- [[_user()_2]] - code - backend/tests/test_kb_migration.py
- [[_utcnow()]] - code - backend/app/services/kb/migrate.py
- [[backup_db()]] - code - backend/app/services/kb/migrate.py
- [[backup_vault()]] - code - backend/app/services/kb/migrate.py
- [[datetime_7]] - code
- [[disable_cross_user_duplicates()]] - code - backend/app/services/kb/migrate.py
- [[force=False (the scheduled path) must gate on KB_AUTO_LOCAL_SYNC_ENABLED]] - rationale - backend/tests/test_kb_migration.py
- [[refresh_file_paths()]] - code - backend/app/services/kb/migrate.py
- [[repoint_source_roots()]] - code - backend/app/services/kb/migrate.py
- [[run_migration()]] - code - backend/app/services/kb/migrate.py
- [[scan_and_ingest()]] - code - backend/app/services/kb/scanner.py
- [[test_kb_migration.py]] - code - backend/tests/test_kb_migration.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_22
SORT file.name ASC
```

## Connections to other communities
- 40 edges to [[_COMMUNITY_Community 2]]
- 5 edges to [[_COMMUNITY_Community 17]]
- 5 edges to [[_COMMUNITY_Community 86]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 3 edges to [[_COMMUNITY_Community 116]]
- 3 edges to [[_COMMUNITY_Community 111]]
- 2 edges to [[_COMMUNITY_Community 9]]
- 2 edges to [[_COMMUNITY_Community 261]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 72]]
- 1 edge to [[_COMMUNITY_Community 48]]

## Top bridge nodes
- [[test_kb_migration.py]] - degree 38, connects to 9 communities
- [[scan_and_ingest()]] - degree 31, connects to 7 communities
- [[run_migration()]] - degree 16, connects to 2 communities
- [[.test_purge_detaches_linked_courses()]] - degree 5, connects to 2 communities
- [[_make_source()_4]] - degree 30, connects to 1 community