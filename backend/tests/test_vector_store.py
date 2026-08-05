"""Tests for the vector store (Zenith-Study-Planner G1, Phase 3)."""
from __future__ import annotations

import pytest

from app.services.vector_store import VectorStore


def test_empty_store_returns_empty():
    store = VectorStore()
    assert store.query([1.0, 0.0, 0.0], k=3) == []
    assert len(store) == 0


def test_add_and_query_nearest_neighbour():
    store = VectorStore()
    store.add(
        ["a", "b", "c"],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )
    results = store.query([1.0, 0.1, 0.0], k=1)
    assert results[0]["id"] == "a"
    assert results[0]["score"] > 0.99


def test_query_returns_top_k_sorted():
    store = VectorStore()
    store.add(
        ["near", "far", "mid"],
        [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
    )
    results = store.query([1.0, 0.0], k=3)
    ids = [r["id"] for r in results]
    scores = [r["score"] for r in results]
    assert ids[0] == "near"
    assert ids[1] == "mid"
    assert ids[2] == "far"
    assert scores == sorted(scores, reverse=True)


def test_replace_same_id_keeps_single_row():
    store = VectorStore()
    store.add(["x"], [[1.0, 0.0]])
    store.add(["x"], [[0.0, 1.0]])
    assert len(store) == 1
    results = store.query([0.0, 1.0], k=1)
    assert results[0]["id"] == "x"
    assert results[0]["score"] > 0.99


def test_delete_removes_vectors():
    store = VectorStore()
    store.add(["a", "b"], [[1.0, 0.0], [0.0, 1.0]])
    store.delete(["a"])
    assert len(store) == 1
    results = store.query([1.0, 0.0], k=1)
    assert results[0]["id"] == "b"  # 'a' gone; b at 0 similarity, still top-1


def test_delete_missing_id_is_noop():
    store = VectorStore()
    store.add(["a"], [[1.0, 0.0]])
    store.delete(["zzz"])
    assert len(store) == 1


def test_clear_empties_store():
    store = VectorStore()
    store.add(["a"], [[1.0, 0.0]])
    store.clear()
    assert len(store) == 0


def test_add_mismatched_lengths_raises():
    store = VectorStore()
    with pytest.raises(ValueError):
        store.add(["a", "b"], [[1.0, 0.0]])


def test_dimension_mismatch_returns_empty():
    store = VectorStore()
    store.add(["a"], [[1.0, 0.0]])
    assert store.query([1.0, 0.0, 0.0], k=1) == []


def test_zero_query_vector_returns_empty():
    store = VectorStore()
    store.add(["a"], [[1.0, 0.0]])
    assert store.query([0.0, 0.0], k=1) == []
