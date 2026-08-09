"""File-backed vector store (Second Brain Phase 2, Idea 12, phrase 14).

Persists the numpy matrix + id list under ``settings.UPLOAD_DIR/kb_index/``
so the index survives process restarts (phrase 19).  A fresh instance
loads existing state automatically; corrupt or missing files fall back
to an empty store (graceful degradation).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import numpy as np

from app.config import settings
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

INDEX_DIR = "kb_index"
MATRIX_FILE = "vectors.npy"
IDS_FILE = "ids.json"


class FileVectorStore(VectorStore):
    """File-backed vector store that persists to disk.

    Mirrors the in-memory ``VectorStore`` interface but saves a
    ``.npy`` matrix and a JSON id list on every ``save()`` call.
    On construction it attempts to load existing files (survives
    restarts).  Missing or corrupt files are ignored and the store
    starts empty.
    """

    def __init__(self, directory: str | None = None) -> None:
        self._directory = directory or os.path.join(
            settings.UPLOAD_DIR, INDEX_DIR
        )
        os.makedirs(self._directory, exist_ok=True)
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None
        self._load()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def save(self) -> None:
        """Write the current matrix + id list to disk."""
        if self._matrix is None or not self._ids:
            # Nothing to persist — remove stale files.
            for fname in (MATRIX_FILE, IDS_FILE):
                path = os.path.join(self._directory, fname)
                if os.path.exists(path):
                    os.remove(path)
            return
        np.save(
            os.path.join(self._directory, MATRIX_FILE),
            self._matrix,
        )
        with open(os.path.join(self._directory, IDS_FILE), "w", encoding="utf-8") as fh:
            json.dump(self._ids, fh)

    def _load(self) -> None:
        """Load persisted state if present; silently ignore corruption."""
        matrix_path = os.path.join(self._directory, MATRIX_FILE)
        ids_path = os.path.join(self._directory, IDS_FILE)
        if not os.path.exists(matrix_path) or not os.path.exists(ids_path):
            return
        try:
            self._matrix = np.load(matrix_path)
            with open(ids_path, "r", encoding="utf-8") as fh:
                self._ids = json.load(fh)
            if not isinstance(self._ids, list):
                raise ValueError("ids.json is not a list")
            if self._matrix is not None and self._matrix.shape[0] != len(self._ids):
                logger.warning(
                    "Vector store mismatch: %d ids vs %d rows; resetting",
                    len(self._ids),
                    self._matrix.shape[0],
                )
                self._ids = []
                self._matrix = None
        except Exception as exc:  # noqa: BLE001 — corrupt files, graceful fallback
            logger.warning("Failed to load vector store index (%s); starting empty", exc)
            self._ids = []
            self._matrix = None

    # ------------------------------------------------------------------ #
    # Mutation (overrides to keep file in sync)
    # ------------------------------------------------------------------ #
    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        super().add(ids, vectors)
        self.save()

    def delete(self, ids: list[str]) -> None:
        super().delete(ids)
        self.save()

    def clear(self) -> None:
        super().clear()
        self.save()

    # ------------------------------------------------------------------ #
    # Query (inherited — no file I/O needed)
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        return len(self._ids)


# --------------------------------------------------------------------------- #
# Module-level singleton — the same pattern as vector_store.py.
# --------------------------------------------------------------------------- #
_file_store: FileVectorStore | None = None


def get_file_store() -> FileVectorStore:
    """Return the shared file-backed store singleton."""
    global _file_store  # noqa: PLW0603
    if _file_store is None:
        _file_store = FileVectorStore()
    return _file_store
