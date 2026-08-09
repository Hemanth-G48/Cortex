"""Retrieval evaluation harness (Phase 3, Idea 26, phrases 51–60).

Loads golden sets from ``backend/tests/fixtures/kb_eval/*.json``, runs offline
retrieval in the three ``KB_SEARCH_MODE``s, computes recall@k / precision@k /
MRR, and records each run into ``kb_eval_runs`` for trend tracking.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import KbEvalRun
from app.services.kb.eval_metrics import evaluate
from app.services.kb.search import KbSearcher

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "kb_eval"


def load_golden_set(path: Path) -> list[dict]:
    """Load a golden-set JSON file: [{query, relevant_chunk_ids, subject}]."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = []
    for entry in data:
        if not isinstance(entry, dict) or not entry.get("query"):
            continue
        relevant = [int(i) for i in entry.get("relevant_chunk_ids", [])]
        items.append(
            {
                "query": entry["query"],
                "subject": entry.get("subject", ""),
                "relevant_chunk_ids": relevant,
            }
        )
    return items


def run_eval(
    db: Session,
    user_id: int,
    mode: str = "hybrid",
    k: int = 10,
    fixture_dir: Path | None = None,
    persist: bool = True,
) -> list[dict]:
    """Run every golden query in ``mode`` and compute aggregate metrics.

    Returns per-query rows (for the dashboard) and persists a ``KbEvalRun``
    summary row when ``persist`` is true.
    """
    fixture_dir = fixture_dir or DEFAULT_FIXTURE_DIR
    runs: list[dict] = []
    searcher = KbSearcher(db, user_id)
    for path in sorted(fixture_dir.glob("*.json")):
        golden = load_golden_set(path)
        if not golden:
            continue
        results: list[tuple[list[int], set[int]]] = []
        for entry in golden:
            resp = searcher.search(
                entry["query"],
                mode=mode,
                limit=max(k, 10),
                page=1,
            )
            retrieved = [item["chunk_id"] for item in resp["items"]]
            results.append((retrieved, set(entry["relevant_chunk_ids"])))
        metrics = evaluate(results, k=k)
        runs.append(
            {
                "golden_set": path.stem,
                "queries": metrics["queries"],
                "recall@k": metrics[f"recall@{k}"],
                "precision@k": metrics[f"precision@{k}"],
                "mrr": metrics["mrr"],
            }
        )
        if persist:
            db.add(
                KbEvalRun(
                    user_id=user_id,
                    golden_set=path.stem,
                    mode=mode,
                    queries=metrics["queries"],
                    recall_at_k=metrics[f"recall@{k}"],
                    precision_at_k=metrics[f"precision@{k}"],
                    mrr=metrics["mrr"],
                )
            )
    if persist:
        db.commit()
    return runs


__all__ = ["load_golden_set", "run_eval", "DEFAULT_FIXTURE_DIR"]
