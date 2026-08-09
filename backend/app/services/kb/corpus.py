"""Per-user corpus cache for the reindex pipeline (shared TF-IDF data).

The deterministic fallbacks (``concepts.tfidf_concepts`` and
``tagger.tfidf_tag_candidates``) both re-scan the *entire* user corpus per
document — one chunk query per document plus a full re-tokenization — which
makes a large reindex quadratic (N+1 queries × N documents).

This module loads the corpus once per user with two batched queries, stores
**plain data only** (no ORM instances, so it is safe to share across
sessions/threads), and caches it keyed by ``(engine identity, user_id,
signature)`` where the signature is ``(doc_count, chunk_count,
max_chunk_id)`` — any new/changed/removed document or chunk changes the
signature and forces a reload.  The cache is single-entry (last user wins),
which bounds memory and matches the single-active-user job model.

Consumers keep their own tokenizers; the corpus provides lazy per-tokenizer
token views so each consumer's exact tokenization semantics are preserved.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument

logger = logging.getLogger(__name__)

_lock = threading.Lock()
# (engine_id, user_id, signature) -> UserCorpus
_cache: tuple[tuple, UserCorpus] | None = None


def _signature(db: Session, user_id: int) -> tuple:
    """Cheap fingerprint of the user's corpus (2 aggregate queries)."""
    n_docs = (
        db.query(func.count(KbDocument.id))
        .filter(KbDocument.user_id == user_id)
        .scalar()
        or 0
    )
    n_chunks, max_chunk = (
        db.query(func.count(KbChunk.id), func.max(KbChunk.id))
        .filter(KbChunk.user_id == user_id)
        .one()
    )
    return (n_docs, n_chunks or 0, max_chunk or 0)


@dataclass
class UserCorpus:
    """Immutable per-user corpus of plain data (no ORM instances)."""

    user_id: int
    # doc_id -> chunk contents in sequence order (empty list = no chunks).
    doc_texts: dict[int, list[str]] = field(default_factory=dict)
    # doc_id -> path_rel / title (for graph path resolution).
    doc_paths: dict[int, str] = field(default_factory=dict)
    doc_titles: dict[int, str] = field(default_factory=dict)
    # Lazy per-tokenizer views: name -> {doc_id: tokens}.
    _flat_tokens: dict[str, dict[int, list[str]]] = field(default_factory=dict)
    _chunk_tokens: dict[str, dict[int, list[list[str]]]] = field(default_factory=dict)
    # Lazy derived views (e.g. IDF maps) keyed by consumer name.
    _views: dict[str, object] = field(default_factory=dict)

    def cached(self, name: str, builder: Callable[[], object]) -> object:
        """Memoize an arbitrary derived value for this corpus instance.

        The corpus is immutable after load (fresh instance on signature
        change), so any pure function of it can be computed exactly once.
        """
        view = self._views.get(name)
        if view is None:
            view = builder()
            self._views[name] = view
        return view

    def flat_tokens(
        self, name: str, tokenize: Callable[[str], list[str]]
    ) -> dict[int, list[str]]:
        """Per-document flat token list (all chunks joined, then tokenized).

        Matches ``concepts.tfidf_concepts``' ``_tokenize(" ".join(texts))``.
        """
        view = self._flat_tokens.get(name)
        if view is None:
            view = {
                doc_id: tokenize(" ".join(texts))
                for doc_id, texts in self.doc_texts.items()
            }
            self._flat_tokens[name] = view
        return view

    def chunk_tokens(
        self, name: str, tokenize: Callable[[str], list[str]]
    ) -> dict[int, list[list[str]]]:
        """Per-document list of per-chunk token lists.

        Matches ``tagger.tfidf_tag_candidates``' per-chunk tokenization.
        """
        view = self._chunk_tokens.get(name)
        if view is None:
            view = {
                doc_id: [tokenize(text) for text in texts]
                for doc_id, texts in self.doc_texts.items()
            }
            self._chunk_tokens[name] = view
        return view


def _load(db: Session, user_id: int) -> UserCorpus:
    """Two batched queries build the whole corpus (docs + all chunks)."""
    docs = (
        db.query(KbDocument.id, KbDocument.path_rel, KbDocument.title)
        .filter(KbDocument.user_id == user_id)
        .order_by(KbDocument.id)
        .all()
    )
    corpus = UserCorpus(user_id=user_id)
    for row in docs:
        corpus.doc_paths[row[0]] = row[1] or ""
        corpus.doc_titles[row[0]] = row[2] or ""
        corpus.doc_texts[row[0]] = []

    chunks = (
        db.query(KbChunk.document_id, KbChunk.content)
        .filter(KbChunk.user_id == user_id)
        .order_by(KbChunk.document_id, KbChunk.seq)
        .all()
    )
    for doc_id, content in chunks:
        # Only attach to documents that actually exist (orphaned chunk rows
        # are ignored — matches the original per-document query semantics).
        if doc_id in corpus.doc_texts:
            corpus.doc_texts[doc_id].append(content)
    return corpus


def get_user_corpus(db: Session, user_id: int) -> UserCorpus:
    """Return the (cached) corpus for *user_id* on *db*'s engine.

    The engine identity is part of the key so the app's SQLite file and a
    test's in-memory database never share cached data.
    """
    global _cache
    engine_id = id(db.get_bind())
    sig = _signature(db, user_id)
    with _lock:
        if _cache is not None and _cache[0] == (engine_id, user_id, sig):
            return _cache[1]
    corpus = _load(db, user_id)
    with _lock:
        _cache = ((engine_id, user_id, sig), corpus)
    return corpus


def clear_user_corpus() -> None:
    """Drop the cached corpus (tests / explicit invalidation)."""
    global _cache
    with _lock:
        _cache = None
