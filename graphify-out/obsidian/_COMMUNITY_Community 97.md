---
type: community
cohesion: 0.10
members: 30
---

# Community 97

**Cohesion:** 0.10 - loosely connected
**Members:** 30 nodes

## Members
- [[.test_load_golden_set()]] - code - backend/tests/test_kb_eval.py
- [[.test_run_eval_persists_rows()]] - code - backend/tests/test_kb_eval.py
- [[1rank of the first relevant chunk (0 if none retrieved).]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Aggregate metrics over ``(retrieved_ids, relevant_ids)`` pairs.      Returns ``{]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Base_35]] - code
- [[Fraction of relevant chunks present in the top-k retrieved list.]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Fraction of the top-k retrieved chunks that are relevant.]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Idea 26 — retrieval evaluation harness tests.  The metric functions must be math]] - rationale - backend/tests/test_kb_eval.py
- [[KbEvalRun]] - code - backend/app/models/kb/eval_run.py
- [[KbEvalRun model — retrieval evaluation run (Phase 3, Idea 26).  Stores one row p]] - rationale - backend/app/models/kb/eval_run.py
- [[Load a golden-set JSON file {query, relevant_chunk_ids, subject}.]] - rationale - backend/app/services/kb/eval_harness.py
- [[MRR over a collection of per-query reciprocal ranks.]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Path_4]] - code
- [[Retrieval evaluation harness (Phase 3, Idea 26, phrases 51–60).  Loads golden se]] - rationale - backend/app/services/kb/eval_harness.py
- [[Retrieval evaluation metrics (Phase 3, Idea 26, phrase 54).  Pure functions over]] - rationale - backend/app/services/kb/eval_metrics.py
- [[Run every golden query in ``mode`` and compute aggregate metrics.      Returns p]] - rationale - backend/app/services/kb/eval_harness.py
- [[Session_149]] - code
- [[TestGoldenSet]] - code - backend/tests/test_kb_eval.py
- [[TestHarnessPersist]] - code - backend/tests/test_kb_eval.py
- [[eval_harness.py]] - code - backend/app/services/kb/eval_harness.py
- [[eval_metrics.py]] - code - backend/app/services/kb/eval_metrics.py
- [[eval_run.py]] - code - backend/app/models/kb/eval_run.py
- [[evaluate()]] - code - backend/app/services/kb/eval_metrics.py
- [[load_golden_set()]] - code - backend/app/services/kb/eval_harness.py
- [[mean_reciprocal_rank()]] - code - backend/app/services/kb/eval_metrics.py
- [[precision_at_k()]] - code - backend/app/services/kb/eval_metrics.py
- [[recall_at_k()]] - code - backend/app/services/kb/eval_metrics.py
- [[reciprocal_rank()]] - code - backend/app/services/kb/eval_metrics.py
- [[run_eval()_1]] - code - backend/app/services/kb/eval_harness.py
- [[test_kb_eval.py]] - code - backend/tests/test_kb_eval.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_97
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 243]]
- 3 edges to [[_COMMUNITY_Community 10]]
- 3 edges to [[_COMMUNITY_Community 135]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 1 edge to [[_COMMUNITY_Community 319]]

## Top bridge nodes
- [[test_kb_eval.py]] - degree 11, connects to 3 communities
- [[run_eval()_1]] - degree 13, connects to 2 communities
- [[eval_harness.py]] - degree 10, connects to 2 communities
- [[KbEvalRun]] - degree 8, connects to 2 communities
- [[eval_run.py]] - degree 4, connects to 2 communities