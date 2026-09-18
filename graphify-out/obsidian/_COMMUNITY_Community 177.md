---
type: community
cohesion: 0.14
members: 19
---

# Community 177

**Cohesion:** 0.14 - loosely connected
**Members:** 19 nodes

## Members
- [[.cached()]] - code - backend/app/services/kb/corpus.py
- [[.chunk_tokens()]] - code - backend/app/services/kb/corpus.py
- [[.flat_tokens()]] - code - backend/app/services/kb/corpus.py
- [[Cheap fingerprint of the user's corpus (2 aggregate queries).]] - rationale - backend/app/services/kb/corpus.py
- [[Drop the cached corpus (tests  explicit invalidation).]] - rationale - backend/app/services/kb/corpus.py
- [[Immutable per-user corpus of plain data (no ORM instances).]] - rationale - backend/app/services/kb/corpus.py
- [[Memoize an arbitrary derived value for this corpus instance.          The corpus]] - rationale - backend/app/services/kb/corpus.py
- [[Per-document flat token list (all chunks joined, then tokenized).          Match]] - rationale - backend/app/services/kb/corpus.py
- [[Per-document list of per-chunk token lists.          Matches ``tagger.tfidf_tag_]] - rationale - backend/app/services/kb/corpus.py
- [[Per-user corpus cache for the reindex pipeline (shared TF-IDF data).  The determ]] - rationale - backend/app/services/kb/corpus.py
- [[Return the (cached) corpus for user_id on db's engine.      The engine ident]] - rationale - backend/app/services/kb/corpus.py
- [[Session_144]] - code
- [[Two batched queries build the whole corpus (docs + all chunks).]] - rationale - backend/app/services/kb/corpus.py
- [[UserCorpus]] - code - backend/app/services/kb/corpus.py
- [[_load()]] - code - backend/app/services/kb/corpus.py
- [[_signature()]] - code - backend/app/services/kb/corpus.py
- [[clear_user_corpus()]] - code - backend/app/services/kb/corpus.py
- [[corpus.py]] - code - backend/app/services/kb/corpus.py
- [[get_user_corpus()]] - code - backend/app/services/kb/corpus.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_177
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Community 2]]
- 2 edges to [[_COMMUNITY_Community 37]]
- 2 edges to [[_COMMUNITY_Community 92]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[get_user_corpus()]] - degree 10, connects to 2 communities
- [[corpus.py]] - degree 9, connects to 2 communities