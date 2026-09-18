---
type: community
cohesion: 0.09
members: 35
---

# Community 81

**Cohesion:** 0.09 - loosely connected
**Members:** 35 nodes

## Members
- [[0–1 groundedness citation coverage × token overlap with sources.]] - rationale - backend/app/services/kb/rag.py
- [[Budget-capped LLM rerank returning chunk ids best-first, or None.]] - rationale - backend/app/services/kb/rag.py
- [[Compose the full pipeline; returns stage timing + result (phrase 21).]] - rationale - backend/app/services/kb/rag.py
- [[Direct documentdocument neighbors (via doc edges + shared concepts).]] - rationale - backend/app/services/kb/fusion.py
- [[Expand a resolved hit list via graph neighbors.      ``hits`` are unified search]] - rationale - backend/app/services/kb/fusion.py
- [[Expand aliasestypos (and LLM-rewrite when enabled). Returns both.]] - rationale - backend/app/services/kb/rag.py
- [[ExpandedHit]] - code - backend/app/services/kb/fusion.py
- [[First chunk id per document (cheap approximation for snippet display).]] - rationale - backend/app/services/kb/fusion.py
- [[Generate an answer from retrieval with the faithfulness gate (phrase 26).      U]] - rationale - backend/app/services/kb/rag.py
- [[Human-readable prerequisite chains for prompt injection (phrase 34).      ``B b]] - rationale - backend/app/services/kb/fusion.py
- [[Idea 93 — full RAG pipeline hardening.  Refactors retrieval into composable stag]] - rationale - backend/app/services/kb/rag.py
- [[Idea 94 — knowledge-graph + vector fusion.  Two-stage retrieval vectorhybrid t]] - rationale - backend/app/services/kb/fusion.py
- [[Map answer claims to source chunk ids (chunk-id map, not free text).]] - rationale - backend/app/services/kb/rag.py
- [[One graph-expanded candidate.]] - rationale - backend/app/services/kb/fusion.py
- [[Prompt for a RAG-grounded tutor answer (Idea 61, phrase 4).      ``context`` is]] - rationale - backend/app/services/prompts.py
- [[Rerank the fused top-N (deterministic term-overlap; LLM when budgeted).]] - rationale - backend/app/services/kb/rag.py
- [[Session_154]] - code
- [[Session_184]] - code
- [[_blocks()]] - code - backend/app/services/kb/rag.py
- [[_fallback()]] - code - backend/app/services/kb/rag.py
- [[_first_chunk_map()]] - code - backend/app/services/kb/fusion.py
- [[_llm_rerank()]] - code - backend/app/services/kb/rag.py
- [[_neighbor_docs()]] - code - backend/app/services/kb/fusion.py
- [[_stage_enabled()]] - code - backend/app/services/kb/rag.py
- [[faithfulness()]] - code - backend/app/services/kb/rag.py
- [[fusion.py]] - code - backend/app/services/kb/fusion.py
- [[generate_grounded()]] - code - backend/app/services/kb/rag.py
- [[graph_expand()]] - code - backend/app/services/kb/fusion.py
- [[prerequisite_chains()]] - code - backend/app/services/kb/fusion.py
- [[rag.py]] - code - backend/app/services/kb/rag.py
- [[rerank()]] - code - backend/app/services/kb/rag.py
- [[rewrite_query()]] - code - backend/app/services/kb/rag.py
- [[run_pipeline()]] - code - backend/app/services/kb/rag.py
- [[tutor_chat_prompt()]] - code - backend/app/services/prompts.py
- [[verify_citations()]] - code - backend/app/services/kb/rag.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_81
SORT file.name ASC
```

## Connections to other communities
- 14 edges to [[_COMMUNITY_Community 1]]
- 8 edges to [[_COMMUNITY_Community 135]]
- 3 edges to [[_COMMUNITY_Community 2]]
- 3 edges to [[_COMMUNITY_Community 54]]
- 3 edges to [[_COMMUNITY_Community 74]]
- 3 edges to [[_COMMUNITY_Community 73]]
- 2 edges to [[_COMMUNITY_Community 201]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 221]]
- 1 edge to [[_COMMUNITY_Community 217]]
- 1 edge to [[_COMMUNITY_Community 146]]
- 1 edge to [[_COMMUNITY_Community 103]]

## Top bridge nodes
- [[rag.py]] - degree 30, connects to 7 communities
- [[fusion.py]] - degree 15, connects to 6 communities
- [[generate_grounded()]] - degree 12, connects to 3 communities
- [[graph_expand()]] - degree 10, connects to 2 communities
- [[rerank()]] - degree 8, connects to 2 communities