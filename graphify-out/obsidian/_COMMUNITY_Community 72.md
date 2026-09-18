---
type: community
cohesion: 0.09
members: 39
---

# Community 72

**Cohesion:** 0.09 - loosely connected
**Members:** 39 nodes

## Members
- [[.ensure_schema()]] - code - backend/app/services/kb/fts.py
- [[.ensure_schema()_2]] - code - backend/app/services/kb/fts.py
- [[.ensure_schema()_1]] - code - backend/app/services/kb/fts.py
- [[.rebuild()]] - code - backend/app/services/kb/fts.py
- [[.rebuild()_2]] - code - backend/app/services/kb/fts.py
- [[.rebuild()_1]] - code - backend/app/services/kb/fts.py
- [[.search()]] - code - backend/app/services/kb/fts.py
- [[.search()_2]] - code - backend/app/services/kb/fts.py
- [[.search()_1]] - code - backend/app/services/kb/fts.py
- [[ABC]] - code
- [[Abstraction over the full-text index (SQLite FTS5  Postgres tsvector).]] - rationale - backend/app/services/kb/fts.py
- [[Any_11]] - code
- [[Backfill the index from kb_chunks; returns row count.]] - rationale - backend/app/services/kb/fts.py
- [[Create the FTS5 table + sync triggers idempotently on ``engine``.      Called by]] - rationale - backend/app/services/kb/fts.py
- [[Create the index + sync triggers idempotently.]] - rationale - backend/app/services/kb/fts.py
- [[Engine]] - code
- [[Ensure the FTS schema exists on the given engine, if enabled.      Used by ``KbS]] - rationale - backend/app/services/kb/fts.py
- [[Escape a bare term against FTS5 special chars.]] - rationale - backend/app/services/kb/fts.py
- [[FtsBackend]] - code - backend/app/services/kb/fts.py
- [[Full-text search (Idea 21).  Dev backend SQLite FTS5 virtual table ``kb_fts`` s]] - rationale - backend/app/services/kb/fts.py
- [[Idempotent startup hook create the FTS index if enabled (phrase 2).]] - rationale - backend/app/services/kb/fts.py
- [[Lowercase, strip punctuation, split into word tokens (phrase 5).      Stopwords]] - rationale - backend/app/services/kb/fts.py
- [[Postgres ``tsvector`` + GIN path (prod, phrase 4).      Documented seam the rea]] - rationale - backend/app/services/kb/fts.py
- [[PostgresFtsBackend]] - code - backend/app/services/kb/fts.py
- [[Ranked chunks {chunk_id, document_id, seq, snippet, rank}.]] - rationale - backend/app/services/kb/fts.py
- [[Reconcile the FTS index + triggers with ``kb_chunks``.      Handles three diverg]] - rationale - backend/app/services/kb/fts.py
- [[Return the backend matching the configured database driver.]] - rationale - backend/app/services/kb/fts.py
- [[SQLite FTS5 virtual table + triggers (dev, and the test backend).]] - rationale - backend/app/services/kb/fts.py
- [[SQLiteFtsBackend]] - code - backend/app/services/kb/fts.py
- [[Translate a raw query into an FTS5 match expression.      ``phrase here`` → qu]] - rationale - backend/app/services/kb/fts.py
- [[_ensure_fts_ddl()]] - code - backend/app/services/kb/fts.py
- [[_escape_term()]] - code - backend/app/services/kb/fts.py
- [[_heal_drift()]] - code - backend/app/services/kb/fts.py
- [[build_fts_query()]] - code - backend/app/services/kb/fts.py
- [[ensure_fts_schema()]] - code - backend/app/services/kb/fts.py
- [[ensure_fts_schema_for()]] - code - backend/app/services/kb/fts.py
- [[fts.py]] - code - backend/app/services/kb/fts.py
- [[get_fts_backend()]] - code - backend/app/services/kb/fts.py
- [[tokenize_query()]] - code - backend/app/services/kb/fts.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_72
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 243]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 135]]
- 1 edge to [[_COMMUNITY_Community 5]]
- 1 edge to [[_COMMUNITY_Community 220]]
- 1 edge to [[_COMMUNITY_Community 111]]
- 1 edge to [[_COMMUNITY_Community 22]]

## Top bridge nodes
- [[fts.py]] - degree 19, connects to 6 communities
- [[ensure_fts_schema()]] - degree 7, connects to 2 communities
- [[get_fts_backend()]] - degree 9, connects to 1 community
- [[ensure_fts_schema_for()]] - degree 7, connects to 1 community