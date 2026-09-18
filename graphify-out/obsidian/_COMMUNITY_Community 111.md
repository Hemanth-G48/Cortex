---
type: community
cohesion: 0.10
members: 27
---

# Community 111

**Cohesion:** 0.10 - loosely connected
**Members:** 27 nodes

## Members
- [[Dedicated automation timer — independent of watcher mode (watchdog or     pollin]] - rationale - backend/app/services/kb/watcher.py
- [[Event hook after a source scan, refresh KB-derived courses.      Cheap (bounded]] - rationale - backend/app/services/kb/watcher.py
- [[Expected embedding dimension for the configured local model.      Currently the]] - rationale - backend/app/services/embeddings.py
- [[Folder watcher (Idea 3, phrases 28–29).  An optional ``watchdog`` observer (nati]] - rationale - backend/app/services/kb/watcher.py
- [[Lazily load the shared fastembed TextEmbedding model (thread-safe).      Uses CU]] - rationale - backend/app/services/embeddings.py
- [[Load the pip-shipped CUDA runtime libs so onnxruntime-gpu can use them.      ``o]] - rationale - backend/app/services/embeddings.py
- [[Periodic automation pass — drives every KB_AUTO_ job on a timer.      Runs at m]] - rationale - backend/app/services/kb/watcher.py
- [[Prefer a native watchdog observer; falls back to polling on ImportError.]] - rationale - backend/app/services/kb/watcher.py
- [[Run ``fn`` retrying on SQLite ``database is locked``.      The API server and th]] - rationale - backend/app/services/kb/watcher.py
- [[Start the watcher (idempotent). Pass a factory in tests, else app default.]] - rationale - backend/app/services/kb/watcher.py
- [[Stop the watcher, the automation timer, and any in-flight threads.]] - rationale - backend/app/services/kb/watcher.py
- [[True when the local fastembed model is selectable.      Requires ``EMBEDDINGS_BA]] - rationale - backend/app/services/embeddings.py
- [[_auto_loop()]] - code - backend/app/services/kb/watcher.py
- [[_get_fastembed()]] - code - backend/app/services/embeddings.py
- [[_maybe_derive_courses()]] - code - backend/app/services/kb/watcher.py
- [[_maybe_run_automations()]] - code - backend/app/services/kb/watcher.py
- [[_poll_loop()]] - code - backend/app/services/kb/watcher.py
- [[_poll_once()]] - code - backend/app/services/kb/watcher.py
- [[_preload_nvidia_libs()]] - code - backend/app/services/embeddings.py
- [[_retry_locked()]] - code - backend/app/services/kb/watcher.py
- [[_start_watchdog()]] - code - backend/app/services/kb/watcher.py
- [[fastembed_available()]] - code - backend/app/services/embeddings.py
- [[fastembed_dim()]] - code - backend/app/services/embeddings.py
- [[lifespan()]] - code - backend/main.py
- [[start_watcher()]] - code - backend/app/services/kb/watcher.py
- [[stop_watcher()]] - code - backend/app/services/kb/watcher.py
- [[watcher.py]] - code - backend/app/services/kb/watcher.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_111
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 2]]
- 3 edges to [[_COMMUNITY_Community 17]]
- 3 edges to [[_COMMUNITY_Community 22]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 75]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 261]]
- 1 edge to [[_COMMUNITY_Community 51]]
- 1 edge to [[_COMMUNITY_Community 94]]
- 1 edge to [[_COMMUNITY_Community 72]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[watcher.py]] - degree 18, connects to 7 communities
- [[lifespan()]] - degree 10, connects to 6 communities
- [[_maybe_run_automations()]] - degree 6, connects to 2 communities
- [[_poll_once()]] - degree 6, connects to 2 communities
- [[fastembed_available()]] - degree 5, connects to 1 community