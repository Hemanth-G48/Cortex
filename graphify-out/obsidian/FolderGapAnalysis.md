---
source_file: "backend/app/models/kb/folder_gap.py"
type: "code"
community: "Community 18"
location: "L25"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# FolderGapAnalysis

## Connections
- [[Base_38]] - `inherits` [EXTRACTED]
- [[domain_service.py]] - `imports` [EXTRACTED]
- [[folder_gap.py]] - `contains` [EXTRACTED]
- [[invalidate_domain_gaps()]] - `indirect_call` [INFERRED]
- [[load_saved_domain_gaps()]] - `indirect_call` [INFERRED]
- [[migrate.py]] - `imports` [EXTRACTED]
- [[models__init__.py]] - `imports` [EXTRACTED]
- [[modelskb__init__.py]] - `imports` [EXTRACTED]
- [[purge_source()]] - `indirect_call` [INFERRED]
- [[save_domain_gaps()]] - `calls` [EXTRACTED]
- [[sync_all_folders()]] - `indirect_call` [INFERRED]
- [[test_kb_folders.py]] - `imports` [EXTRACTED]
- [[test_sync_cleans_domain_gaps_with_stale_folder()]] - `indirect_call` [INFERRED]

#graphify/code #graphify/EXTRACTED #community/Community_18