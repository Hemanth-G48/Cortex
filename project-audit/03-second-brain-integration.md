# Second Brain Integration Analysis

## Integration Architecture

### Connection Mechanism
The Second Brain connects via **local folder scanning** — not a cloud API.
```
Config:
  KB_WATCH_ENABLED: True
  KB_WATCH_POLL_INTERVAL: 30 (seconds)
  
Source types: local folder paths (e.g., /path/to/obsidian/vault)
```

### How Data Flows
```
1. User adds a KB Source (folder path)
2. Watcher polls the folder every 30 seconds
3. Scanner detects new/changed/deleted files
4. Parser extracts markdown structure (headings, links, tags)
5. Chunker splits into 1200-char chunks (150 overlap)
6. Embedder generates 384-dim vectors (fastembed ONNX)
7. FTS5 index built for keyword search
8. Vector store indexed for semantic search
9. Concepts extracted via NLP
10. Edges computed (embedding similarity + LLM)
11. Auto-subject detection from folder names
12. Course sync from `course:*` tags
```

### Vault Structure Expected
```
Second Brain/
├── notes/
│   ├── topic1.md
│   ├── topic2.md
│   └── subfolder/
│       └── nested.md
├── daily-life/
│   └── (daily notes)
└── (other vault content)
```

### Frontend → Backend → Second Brain Flow
```
UI Component (e.g., VaultSearch)
  ↓
endpoints.kb.search(query, domains)
  ↓
POST /api/search { query, domains }
  ↓
Backend: search.py
  ├── FTS5 keyword search
  ├── Vector similarity search
  └── Hybrid fusion (RRF)
  ↓
Response: { results[], total, mode }
  ↓
UI renders results
```

## What Currently Works

1. ✅ Folder scanning and document indexing
2. ✅ Markdown parsing and chunking
3. ✅ Embedding generation (fastembed)
4. ✅ FTS5 keyword search
5. ✅ Semantic search (vector similarity)
6. ✅ Hybrid search (keyword + semantic fusion)
7. ✅ Knowledge graph visualization (sigma.js)
8. ✅ Course derivation from `course:*` tags
9. ✅ Auto-subject detection from folders
10. ✅ Document quality scoring
11. ✅ Concept extraction
12. ✅ Near-duplicate detection
13. ✅ AI tutor (RAG over vault chunks)
14. ✅ Flashcard generation from vault content
15. ✅ Gap analysis per subject/domain

## What Is Missing or Broken

### Missing Flows
1. **No real-time sync notification** — changes require polling
2. **No conflict handling** — concurrent edits not managed
3. **No incremental embedding** — full re-embed on reindex
4. **No vault change detection UI** — user doesn't see sync status
5. **No vault health dashboard** — no overview of indexing status

### Broken Integrations
1. **Daily Vault** — `second_brain/daily-life/` folder is empty, no daily notes flow
2. **Obsidian vault** — `Obsidian Vault/` folder exists but not connected as KB source
3. **Frontend vault pages** — some pages still use traditional DB notes, not KB documents
4. **Course content** — may show stale data if KB not recently scanned
5. **Search results** — no deduplication between FTS and semantic results

### Integration Gaps
1. **Journal → KB** — journal entries not synced to vault
2. **Tasks → KB** — tasks not linked to relevant KB documents
3. **Habits → KB** — habit logs not reflected in vault analytics
4. **Grades → KB** — grade data not used in learning recommendations
5. **Notes (DB) vs KB Documents** — two separate note systems, not unified

## Dual Data Source Problem

The app has TWO note/note-like systems:
1. **Traditional Notes** (DB `notes` table) — used by Notes.tsx page
2. **KB Documents** (KB pipeline) — used by KnowledgeBase, VaultSearch, CourseDetail

These are **not connected**. A note created in Notes.tsx doesn't appear in KB search, and a KB document doesn't appear in the Notes page.

## Second Brain as Primary Data Source Assessment

| Feature | Current Source | Should Use KB? | Gap |
|---------|---------------|---------------|-----|
| Notes | DB `notes` table | ✅ Yes | Notes page doesn't use KB |
| Search | KB search | ✅ Yes | Working but no DB notes |
| Subjects | DB `courses` + KB folders | ⚠️ Partial | Course derivation works |
| Daily Vault | Empty | ❌ No daily flow | No integration |
| Tasks | DB `tasks` | ⚠️ Optional | Could link to KB docs |
| Study Plans | DB `study_plans` | ⚠️ Partial | Could use KB coverage |
| Flashcards | DB + AI generation | ⚠️ Partial | AI uses KB content |
| Analytics | DB aggregation | ✅ Yes | Working |
| Recommendations | AI + KB | ✅ Yes | Working |
