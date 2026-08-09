"""Search orchestration (Phase 3, Ideas 22–23).

``KbSearcher`` is the single entry point for all retrieval modes:
- ``keyword`` — FTS5 (Idea 21) via ``fts.get_fts_backend()``.
- ``semantic`` — embed the query (Idea 22) and cosine-retrieve over the
  persistent ``kb_embeddings`` rows (Phase 2's source of truth), with a
  deterministic local-fallback embedding when AI is disabled.
- ``hybrid`` — Reciprocal Rank Fusion over both rank lists (Idea 23).

Every retriever is user-scoped and returns the unified result shape
``{chunk_id, document_id, title, snippet, score, mode, source_path, …}``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbEmbedding
from app.services.kb import KbService
from app.services.kb import fts

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """One unified search hit."""

    chunk_id: int
    document_id: int
    seq: int
    title: str
    snippet: str
    score: float
    mode: str
    source_path: str | None
    heading_path: str | None
    doc_type: str
    doc_date: str | None
    char_start: int
    char_end: int
    sources: list[str] | None = None


def _get_embedding() -> Any:
    """Import the embedding client lazily (keeps this module import-safe)."""
    from app.services import embeddings

    return embeddings


def semantic_search(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 20,
    exclude_chunk_ids: set[int] | None = None,
) -> list[dict[str, Any]]:
    """Cosine-retrieve over persisted ``kb_embeddings`` (Idea 22, phrase 13).

    Self-contained: loads the user's embedding rows into a numpy matrix rather
    than depending on the in-memory store being populated (robust while Phase 2
    wiring is incomplete). Returns [] when AI is disabled or the user has no
    embeddings — the caller falls back to keyword.
    """
    embeddings = _get_embedding()
    # Same embedding chain as the stored rows (provider → fastembed → hash), so
    # query vectors live in the same space. Never returns None.
    qvec = embeddings.query_embed(query)

    rows = (
        db.query(KbEmbedding)
        .filter(KbEmbedding.user_id == user_id)
        .order_by(KbEmbedding.chunk_id)
        .all()
    )
    if not rows:
        return []

    matrix = np.zeros((len(rows), len(qvec)), dtype=np.float32)
    ids = []
    chunk_ids = []
    for i, row in enumerate(rows):
        try:
            vec = json.loads(row.vector)
        except (ValueError, TypeError):
            continue
        if len(vec) != len(qvec):
            # Dimension mismatch → refuse (phrase 18 / dimension fallback).
            return []
        matrix[i] = vec
        ids.append(row.id)
        chunk_ids.append(row.chunk_id)
    if not ids:
        return []

    q = np.asarray(qvec, dtype=np.float32)
    qnorm = np.linalg.norm(q)
    if qnorm == 0:
        return []
    row_norms = np.linalg.norm(matrix, axis=1)
    row_norms[row_norms == 0] = 1.0
    sims = (matrix @ q) / (row_norms * qnorm)

    order = np.argsort(sims)[::-1]
    results: list[dict[str, Any]] = []
    for idx in order:
        cid = chunk_ids[idx]
        if exclude_chunk_ids and cid in exclude_chunk_ids:
            continue
        results.append(
            {
                "chunk_id": cid,
                "score": float(sims[idx]),
                "mode": "semantic",
                "sources": ["semantic"],
            }
        )
        if len(results) >= limit:
            break
    return results


def _min_max_normalize(items: list[dict[str, Any]]) -> None:
    """In-place min-max score normalization per retriever (phrase 15)."""
    if not items:
        return
    scores = [i.get("score", 0.0) for i in items]
    lo, hi = min(scores), max(scores)
    span = hi - lo
    for i in items:
        s = i.get("score", 0.0)
        i["score"] = (s - lo) / span if span > 0 else 1.0


def _resolve_chunks(db: Session, user_id: int, chunk_ids: list[int]) -> dict[int, dict[str, Any]]:
    """Resolve chunk ids → unified row dicts in one query (phrase 14)."""
    if not chunk_ids:
        return {}
    rows = (
        db.query(KbChunk, KbDocument)
        .join(KbDocument, KbDocument.id == KbChunk.document_id)
        .filter(KbChunk.id.in_(chunk_ids), KbChunk.user_id == user_id)
        .all()
    )
    out: dict[int, dict[str, Any]] = {}
    for chunk, doc in rows:
        out[chunk.id] = {
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "seq": chunk.seq,
            "title": doc.title or doc.path_rel or f"doc {doc.id}",
            "source_path": doc.path_rel,
            "heading_path": chunk.heading_path,
            "doc_type": doc.doc_type,
            "doc_date": doc.doc_date.isoformat() if doc.doc_date else None,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
        }
    return out


def rrf_fuse(
    rank_lists: list[list[dict[str, Any]]],
    k: int | None = None,
    tie_doc_fn=None,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion (Idea 23, phrase 22).

    ``score = sum(1/(k + rank))`` across retriever rank lists, deduped by
    chunk_id. Deterministic tie-break by score desc then chunk_id asc.
    """
    k = k or settings.KB_RRF_K
    fused: dict[int, dict[str, Any]] = {}
    for rl in rank_lists:
        for rank, item in enumerate(rl, start=1):
            cid = item["chunk_id"]
            entry = fused.setdefault(
                cid, {"chunk_id": cid, "score": 0.0, "sources": []}
            )
            entry["score"] += 1.0 / (k + rank)
            entry["sources"].extend(item.get("sources", []))
            # Preserve first-seen mode for provenance and carry the snippet
            # through so hybrid results keep their highlight text (the tutor
            # and result cards both read ``snippet``).
            entry.setdefault("mode", item.get("mode", "hybrid"))
            if not entry.get("snippet") and item.get("snippet"):
                entry["snippet"] = item["snippet"]
    ranked = sorted(
        fused.values(),
        key=lambda e: (-e["score"], e["chunk_id"]),
    )
    return ranked


class KbSearcher:
    """Single entry point for every retrieval mode."""

    def __init__(self, db: Session, user_id: int) -> None:
        self.db = db
        self.user_id = user_id
        self.engine = db.bind

    # ------------------------------------------------------------------ #
    # Retrievers
    # ------------------------------------------------------------------ #
    def keyword(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        backend = fts.get_fts_backend()
        try:
            # Self-heal: ensure the index exists on this engine (startup hook
            # may not have run for in-memory/test engines).
            fts.ensure_fts_schema_for(self.engine)
            hits = backend.search(self.engine, self.user_id, query, limit=limit)
        except Exception as exc:  # noqa: BLE001 — index may not exist yet
            logger.warning("FTS search failed (%s); returning empty", exc)
            hits = []
        return [
            {
                "chunk_id": h["chunk_id"],
                "snippet": h.get("snippet", ""),
                "mode": "keyword",
                "sources": ["fts"],
            }
            for h in hits
        ]

    def semantic(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return semantic_search(self.db, self.user_id, query, limit=limit)

    # ------------------------------------------------------------------ #
    # Fusion + resolve
    # ------------------------------------------------------------------ #
    def search(
        self,
        query: str,
        mode: str | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        """Run retrieval in the requested mode and resolve to unified results.

        Returns ``{items, total, page, page_size, mode, original_query,
        expanded_query}``.
        """
        mode = (mode or settings.KB_SEARCH_MODE or "hybrid").lower()
        if mode not in ("keyword", "semantic", "hybrid"):
            mode = "hybrid"

        kw_hits: list[dict[str, Any]] = []
        sem_hits: list[dict[str, Any]] = []
        if mode in ("keyword", "hybrid"):
            kw_hits = self.keyword(query, limit=limit * 4)
        if mode in ("semantic", "hybrid"):
            sem_hits = self.semantic(query, limit=limit * 4)

        if mode == "keyword":
            _min_max_normalize(kw_hits)
            fused = kw_hits
        elif mode == "semantic":
            _min_max_normalize(sem_hits)
            fused = sem_hits
        else:
            _min_max_normalize(kw_hits)
            _min_max_normalize(sem_hits)
            fused = rrf_fuse([kw_hits, sem_hits])

        if not fused:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": limit,
                "mode": mode,
                "original_query": query,
                "expanded_query": query,
            }

        resolved = _resolve_chunks(
            self.db, self.user_id, [f["chunk_id"] for f in fused]
        )
        items = []
        for f in fused:
            meta = resolved.get(f["chunk_id"])
            if meta is None:
                continue
            items.append(
                SearchResult(
                    chunk_id=f["chunk_id"],
                    document_id=meta["document_id"],
                    seq=meta["seq"],
                    title=meta["title"],
                    snippet=f.get("snippet", ""),
                    score=round(f.get("score", 0.0), 6),
                    mode=mode,
                    source_path=meta["source_path"],
                    heading_path=meta["heading_path"],
                    doc_type=meta["doc_type"],
                    doc_date=meta["doc_date"],
                    char_start=meta["char_start"],
                    char_end=meta["char_end"],
                    sources=f.get("sources"),
                )
            )

        start = (page - 1) * limit
        paged = items[start : start + limit]
        return {
            "items": [self._to_dict(i) for i in paged],
            "total": len(items),
            "page": page,
            "page_size": limit,
            "mode": mode,
            "original_query": query,
            "expanded_query": query,
        }

    @staticmethod
    def _to_dict(r: SearchResult) -> dict[str, Any]:
        return {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "seq": r.seq,
            "title": r.title,
            "snippet": r.snippet,
            "score": r.score,
            "mode": r.mode,
            "source_path": r.source_path,
            "heading_path": r.heading_path,
            "doc_type": r.doc_type,
            "doc_date": r.doc_date,
            "char_start": r.char_start,
            "char_end": r.char_end,
            "sources": r.sources,
        }


__all__ = [
    "KbSearcher",
    "SearchResult",
    "semantic_search",
    "rrf_fuse",
]
