"""Retrieval evaluation metrics (Phase 3, Idea 26, phrase 54).

Pure functions over ranked retrieval results: ``recall@k``, ``precision@k``,
and ``MRR`` (mean reciprocal rank). Used by the CLI eval harness and the
hermetic pytest suite.
"""

from __future__ import annotations

from typing import Iterable


def recall_at_k(retrieved: Iterable[int], relevant: set[int], k: int | None = None) -> float:
    """Fraction of relevant chunks present in the top-k retrieved list."""
    if not relevant:
        return 0.0
    ranked = list(retrieved)
    if k is not None:
        ranked = ranked[:k]
    hits = sum(1 for cid in ranked if cid in relevant)
    return hits / len(relevant)


def precision_at_k(retrieved: Iterable[int], relevant: set[int], k: int | None = None) -> float:
    """Fraction of the top-k retrieved chunks that are relevant."""
    ranked = list(retrieved)
    if k is not None:
        ranked = ranked[:k]
    if not ranked:
        return 0.0
    hits = sum(1 for cid in ranked if cid in relevant)
    return hits / len(ranked)


def reciprocal_rank(retrieved: Iterable[int], relevant: set[int]) -> float:
    """1/rank of the first relevant chunk (0 if none retrieved)."""
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    per_query: Iterable[float],
) -> float:
    """MRR over a collection of per-query reciprocal ranks."""
    values = list(per_query)
    if not values:
        return 0.0
    return sum(values) / len(values)


def evaluate(
    results: list[tuple[list[int], set[int]]],
    k: int = 10,
) -> dict[str, float]:
    """Aggregate metrics over ``(retrieved_ids, relevant_ids)`` pairs.

    Returns ``{recall@k, precision@k, mrr, queries}``.
    """
    recalls: list[float] = []
    precisions: list[float] = []
    rrs: list[float] = []
    for retrieved, relevant in results:
        recalls.append(recall_at_k(retrieved, relevant, k))
        precisions.append(precision_at_k(retrieved, relevant, k))
        rrs.append(reciprocal_rank(retrieved, relevant))
    n = len(results)
    return {
        f"recall@{k}": (sum(recalls) / n) if n else 0.0,
        f"precision@{k}": (sum(precisions) / n) if n else 0.0,
        "mrr": mean_reciprocal_rank(rrs),
        "queries": n,
    }


__all__ = [
    "recall_at_k",
    "precision_at_k",
    "reciprocal_rank",
    "mean_reciprocal_rank",
    "evaluate",
]
