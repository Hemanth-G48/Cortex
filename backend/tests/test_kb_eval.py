"""Idea 26 — retrieval evaluation harness tests.

The metric functions must be mathematically correct on a known ranking; the
harness runs end-to-end on the tiny ``sample.json`` fixture set; and eval runs
persist into ``kb_eval_runs``.
"""
from __future__ import annotations

from app.models import KbEvalRun
from app.services.kb import eval_metrics as m
from app.services.kb.eval_harness import load_golden_set


class TestMetricsMath:
    def test_recall_at_k(self):
        retrieved = [10, 11, 12, 13]
        relevant = {11, 99}
        assert m.recall_at_k(retrieved, relevant, k=4) == 0.5  # 1 of 2
        assert m.recall_at_k(retrieved, relevant, k=1) == 0.0

    def test_precision_at_k(self):
        retrieved = [10, 11, 12, 13]
        relevant = {11, 99}
        assert m.precision_at_k(retrieved, relevant, k=4) == 0.25  # 1 of 4
        assert m.precision_at_k(retrieved, relevant, k=2) == 0.5

    def test_reciprocal_rank(self):
        assert m.reciprocal_rank([5, 10, 15], {10}) == 0.5  # rank 2
        assert m.reciprocal_rank([5, 6], {10}) == 0.0

    def test_mrr(self):
        assert m.mean_reciprocal_rank([1.0, 0.5]) == 0.75

    def test_evaluate_aggregates(self):
        results = [
            ([1, 2, 3], {1}),  # recall 1/1, prec 1/3, rr 1.0
            ([1, 2, 3], {5}),  # recall 0, prec 0, rr 0
        ]
        agg = m.evaluate(results, k=3)
        assert agg["recall@3"] == 0.5
        assert agg["precision@3"] == (1 / 3) / 2
        assert abs(agg["mrr"] - 0.5) < 1e-9
        assert agg["queries"] == 2


class TestGoldenSet:
    def test_load_golden_set(self, kb_eval_fixture_dir):
        fixture = kb_eval_fixture_dir / "sample.json"
        items = load_golden_set(fixture)
        assert len(items) == 3
        assert items[0]["query"] == "machine learning"
        assert items[0]["relevant_chunk_ids"] == [1, 2]


class TestHarnessPersist:
    def test_run_eval_persists_rows(self, db_session, kb_eval_fixture_dir):
        from app.services.kb.eval_harness import run_eval

        runs = run_eval(db_session, user_id=1, mode="keyword", fixture_dir=kb_eval_fixture_dir)
        assert len(runs) >= 1
        rows = db_session.query(KbEvalRun).all()
        assert len(rows) == len(runs)
        assert rows[0].mode == "keyword"
