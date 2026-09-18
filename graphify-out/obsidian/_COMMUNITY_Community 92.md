---
type: community
cohesion: 0.12
members: 32
---

# Community 92

**Cohesion:** 0.12 - loosely connected
**Members:** 32 nodes

## Members
- [[Auto-tagging service (Phase 2, Idea 14, phrases 31-40).  Seeds inlinerule tags,]] - rationale - backend/app/services/kb/tagger.py
- [[Base_31]] - code
- [[Create-or-reuse a tag by name and attach it to doc as manual.      ``course]] - rationale - backend/app/services/kb/tagger.py
- [[Deterministic TF-IDF fallback over the doc's chunk texts vs the     user's corpu]] - rationale - backend/app/services/kb/tagger.py
- [[Ingest-stage entry point for auto-tagging (phrase 40).      Seeds inlinerule ta]] - rationale - backend/app/services/kb/tagger.py
- [[KbDocument_27]] - code
- [[KbDocumentTag]] - code - backend/app/models/kb/document_tag.py
- [[KbDocumentTag model — document↔tag association (Phase 2, Idea 14).  ``provenance]] - rationale - backend/app/models/kb/document_tag.py
- [[Lowercase alphanumeric tokens, length = 2.]] - rationale - backend/app/services/kb/tagger.py
- [[Match existing (user_id, name) or create a new KbTag row.]] - rationale - backend/app/services/kb/tagger.py
- [[Normalise a tag name for storage.      Plain tags are lowercased and capped at ~]] - rationale - backend/app/services/kb/tagger.py
- [[POS-lite heuristic prefer capitalized or length=4 tokens.]] - rationale - backend/app/services/kb/tagger.py
- [[Promote suggested tags to ``KbDocumentTag`` rows with     ``provenance=manual`]] - rationale - backend/app/services/kb/tagger.py
- [[Remove ``KbDocumentTag`` rows for tag_ids ONLY when their     provenance is ``]] - rationale - backend/app/services/kb/tagger.py
- [[Return True when a document_tags row already exists.]] - rationale - backend/app/services/kb/tagger.py
- [[Rule + persisted-AI + deterministic suggestions — never calls the LLM.]] - rationale - backend/app/services/kb/tagger.py
- [[Run ``propose_tags`` (the only LLM path) and persist its AI rows.      Called by]] - rationale - backend/app/services/kb/tagger.py
- [[Session_202]] - code
- [[_create_or_reuse_tag()]] - code - backend/app/services/kb/tagger.py
- [[_existing_document_tag()]] - code - backend/app/services/kb/tagger.py
- [[_is_noun_like()]] - code - backend/app/services/kb/tagger.py
- [[_tokenize()_1]] - code - backend/app/services/kb/tagger.py
- [[_trim_tag()]] - code - backend/app/services/kb/tagger.py
- [[apply_tags()]] - code - backend/app/services/kb/tagger.py
- [[auto_tag_document()]] - code - backend/app/services/kb/tagger.py
- [[create_document_tag()]] - code - backend/app/services/kb/tagger.py
- [[document_tag.py]] - code - backend/app/models/kb/document_tag.py
- [[persist_ai_suggestions()]] - code - backend/app/services/kb/tagger.py
- [[persisted_suggestions()]] - code - backend/app/services/kb/tagger.py
- [[reject_tags()]] - code - backend/app/services/kb/tagger.py
- [[tagger.py]] - code - backend/app/services/kb/tagger.py
- [[tfidf_tag_candidates()]] - code - backend/app/services/kb/tagger.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_92
SORT file.name ASC
```

## Connections to other communities
- 32 edges to [[_COMMUNITY_Community 44]]
- 14 edges to [[_COMMUNITY_Community 43]]
- 9 edges to [[_COMMUNITY_Community 5]]
- 7 edges to [[_COMMUNITY_Community 117]]
- 7 edges to [[_COMMUNITY_Community 78]]
- 6 edges to [[_COMMUNITY_Community 2]]
- 6 edges to [[_COMMUNITY_Community 167]]
- 5 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 216]]
- 4 edges to [[_COMMUNITY_Community 13]]
- 4 edges to [[_COMMUNITY_Community 30]]
- 3 edges to [[_COMMUNITY_Community 53]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 2 edges to [[_COMMUNITY_Community 75]]
- 2 edges to [[_COMMUNITY_Community 203]]
- 2 edges to [[_COMMUNITY_Community 87]]
- 2 edges to [[_COMMUNITY_Community 45]]
- 2 edges to [[_COMMUNITY_Community 169]]
- 2 edges to [[_COMMUNITY_Community 49]]
- 2 edges to [[_COMMUNITY_Community 191]]
- 2 edges to [[_COMMUNITY_Community 277]]
- 2 edges to [[_COMMUNITY_Community 177]]
- 1 edge to [[_COMMUNITY_Community 70]]
- 1 edge to [[_COMMUNITY_Community 27]]
- 1 edge to [[_COMMUNITY_Community 188]]
- 1 edge to [[_COMMUNITY_Community 19]]
- 1 edge to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 16]]
- 1 edge to [[_COMMUNITY_Community 17]]

## Top bridge nodes
- [[KbDocumentTag]] - degree 73, connects to 25 communities
- [[tagger.py]] - degree 34, connects to 9 communities
- [[auto_tag_document()]] - degree 12, connects to 4 communities
- [[apply_tags()]] - degree 15, connects to 3 communities
- [[create_document_tag()]] - degree 13, connects to 3 communities