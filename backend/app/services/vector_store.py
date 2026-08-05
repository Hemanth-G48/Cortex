"""In-memory vector store with cosine-similarity retrieval.

Zenith-Study-Planner G1 (Phase 3). A thin abstraction so document Q&A
(chat/doc-QA) and friend recommendations (KNN) can share one retrieval path.

Design:
- ``VectorStore`` keeps ``ids`` + a numpy matrix of embeddings in process
  memory. It is *not* persisted — indexes are rebuilt from source documents
  on demand (see the documents router / ``retrieval.py``).
- Default backend is pure numpy (zero extra deps, deterministic).
- If ``VECTOR_STORE_BACKEND=faiss`` is set in the environment *and* the
  optional ``faiss`` package is importable, an FAISS index is used instead
  (swapped behind the same API).
"""

from __future__ import annotations

import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Simple in-memory dense-vector store with cosine retrieval."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None  # shape (n, dim)

    # ------------------------------------------------------------------ #
    # Mutation
    # ------------------------------------------------------------------ #
    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        """Add vectors for the given ids, replacing any existing id."""
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors must have the same length")
        if not ids:
            return

        new = np.asarray(vectors, dtype=np.float32)
        if new.ndim != 2:
            raise ValueError("vectors must be a 2D array")

        incoming = dict(zip(ids, new))
        merged_ids: list[str] = []
        merged_rows: list[np.ndarray] = []

        # Existing rows are kept unless replaced by an incoming id.
        if self._matrix is not None:
            for vid, row in zip(self._ids, self._matrix):
                if vid in incoming:
                    continue
                merged_ids.append(vid)
                merged_rows.append(row)

        for vid, row in incoming.items():
            merged_ids.append(vid)
            merged_rows.append(row)

        if merged_rows:
            self._ids = merged_ids
            self._matrix = np.stack(merged_rows).astype(np.float32)
        else:
            self._ids = []
            self._matrix = None

    def delete(self, ids: list[str]) -> None:
        """Remove vectors for the given ids (missing ids are ignored)."""
        if not ids:
            return
        if self._matrix is None:
            return
        drop = set(ids)
        kept = [
            (vid, row)
            for vid, row in zip(self._ids, self._matrix)
            if vid not in drop
        ]
        if not kept:
            self._ids = []
            self._matrix = None
            return
        self._ids = [vid for vid, _ in kept]
        self._matrix = np.stack([row for _, row in kept]).astype(np.float32)

    def clear(self) -> None:
        self._ids = []
        self._matrix = None

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #
    def query(self, vector: list[float], k: int = 5) -> list[dict]:
        """Return the top-k nearest ids with cosine similarity scores.

        Result items: ``{"id": str, "score": float}`` sorted by descending
        score. Empty list when the store is empty, dimensions mismatch, or
        the query vector is all-zero.
        """
        if not self._ids or self._matrix is None:
            return []
        q = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if self._matrix.shape[1] != q.shape[1]:
            logger.warning(
                "Vector dimension mismatch: store=%d query=%d",
                self._matrix.shape[1], q.shape[1],
            )
            return []

        norm = np.linalg.norm(q, axis=1)
        if norm[0] == 0:
            return []

        denom = np.linalg.norm(self._matrix, axis=1)
        denom[denom == 0] = 1.0  # avoid div-by-zero for zero rows
        sims = (self._matrix @ q.T).ravel() / (denom * norm[0])

        top = np.argsort(sims)[::-1][:k]
        return [{"id": self._ids[idx], "score": float(sims[idx])} for idx in top]

    def __len__(self) -> int:
        return len(self._ids)


# --------------------------------------------------------------------------- #
# Module-level singleton used by services across the app.
# --------------------------------------------------------------------------- #
store = VectorStore()


def get_store() -> VectorStore:
    """Return the shared store instance (swap point for FAISS backend)."""
    backend = getattr(settings, "VECTOR_STORE_BACKEND", "numpy")
    if backend == "faiss":
        try:
            from app.services.vector_store_faiss import get_faiss_store  # noqa: PLC0415

            return get_faiss_store()
        except Exception as exc:  # noqa: BLE001 — graceful fallback to numpy
            logger.warning("FAISS backend unavailable (%s); using numpy store", exc)
    return store
