---
source_file: "backend/app/models/kb/folder.py"
type: "code"
community: "Community 18"
location: "L37"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# KbFolder

## Connections
- [[Base_37]] - `inherits` [EXTRACTED]
- [[_domain_row()]] - `references` [EXTRACTED]
- [[_folder_or_404()]] - `references` [EXTRACTED]
- [[_folder_payload()]] - `references` [EXTRACTED]
- [[domain_detail()]] - `indirect_call` [INFERRED]
- [[domain_gaps()]] - `references` [EXTRACTED]
- [[domain_service.py]] - `imports` [EXTRACTED]
- [[domain_tree()]] - `indirect_call` [INFERRED]
- [[folder.py]] - `contains` [EXTRACTED]
- [[folder_documents()]] - `references` [EXTRACTED]
- [[kb_folders.py]] - `imports` [EXTRACTED]
- [[list_domains()]] - `indirect_call` [INFERRED]
- [[load_saved_domain_gaps()]] - `indirect_call` [INFERRED]
- [[migrate.py]] - `imports` [EXTRACTED]
- [[models__init__.py]] - `imports` [EXTRACTED]
- [[modelskb__init__.py]] - `imports` [EXTRACTED]
- [[purge_source()]] - `indirect_call` [INFERRED]
- [[sync_all_folders()]] - `calls` [EXTRACTED]
- [[test_kb_folders.py]] - `imports` [EXTRACTED]
- [[test_sync_is_idempotent_and_counts_direct_children()]] - `indirect_call` [INFERRED]
- [[test_sync_removes_stale_domain_when_folder_deleted()]] - `indirect_call` [INFERRED]

#graphify/code #graphify/EXTRACTED #community/Community_18