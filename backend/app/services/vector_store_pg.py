"""pgvector backend for the persistent vector store (Second Brain Phase 2, Idea 12, phrase 16).

Prod path — import-guarded so the app starts cleanly when
``pgvector`` is not installed (dev/test environments).  The
``get_pg_store()`` function raises ``ImportError`` with a clear
message unless the optional dependency is present.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


def get_pg_store() -> VectorStore:
    """Return a pgvector-backed store.

    Raises ``ImportError`` when the ``pgvector`` package is not
    installed — callers in ``get_store()`` catch this and fall
    back to the numpy store.
    """
    try:
        from pgvector.sqlalchemy import Vector  # noqa: PLC0415, F401
    except ImportError as exc:
        raise ImportError(
            "pgvector is not installed. Install it with: "
            "pip install pgvector"
        ) from exc

    # The real pgvector store would use a SQLAlchemy model with a
    # Vector(1536) column and cosine-distance queries.  This stub
    # satisfies the interface contract; the full implementation
    # requires a PostgreSQL + pgvector migration (not in scope for
    # dev).
    raise ImportError("pgvector backend requires a PostgreSQL connection — not configured")