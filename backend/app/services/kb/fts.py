"""Full-text search (Idea 21).

Dev backend: SQLite FTS5 virtual table ``kb_fts`` synced by AFTER INSERT /
UPDATE / DELETE triggers on ``kb_chunks`` (phrase 3), so the index never drifts
from rows. Prod path: Postgres generated ``tsvector`` column + GIN index behind
the same ``FtsBackend`` interface (phrase 4) — routers never write backend-
specific SQL.

All queries are user-scoped: the FTS query always filters ``user_id`` (phrase
6). Results carry a ``<mark>``-friendly snippet via FTS5 ``snippet()``.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import settings

logger = logging.getLogger(__name__)

# FTS5 special characters that must be quoted in a query string.
_FTS_SPECIAL = set('+-&|!(){}[]^"~*?:\\')

# Matches a quoted phrase token like "deep learning".
_PHRASE_RE = re.compile(r'"([^"]+)"')

# Filler words never useful for retrieval. FTS AND-joins bare tokens, so a
# natural-language query like "what is linear regression?" must drop the
# stopwords or zero chunks match. Mirrors tagger.STOPWORDS (Phase 3, Idea 24).
STOPWORDS = frozenset(
    "a an the and or but in on at to for of with by from as is are was were "
    "be been being have has had do does did will would shall should may might "
    "can could must need dare not no nor so if then than too very just about "
    "also into over after before between under again further once here there "
    "when where why how all each every both few more most other some such "
    "only own same this that these those it its he she they them their his "
    "her our my your me him us you what which who whom whose".split()
)


class FtsBackend(ABC):
    """Abstraction over the full-text index (SQLite FTS5 / Postgres tsvector)."""

    @abstractmethod
    def ensure_schema(self, engine: Engine) -> None:
        """Create the index + sync triggers idempotently."""

    @abstractmethod
    def rebuild(self, engine: Engine) -> int:
        """Backfill the index from kb_chunks; returns row count."""

    @abstractmethod
    def search(
        self,
        engine: Engine,
        user_id: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Ranked chunks: [{chunk_id, document_id, seq, snippet, rank}]."""


class SQLiteFtsBackend(FtsBackend):
    """SQLite FTS5 virtual table + triggers (dev, and the test backend)."""

    def ensure_schema(self, engine: Engine) -> None:
        _ensure_fts_ddl(engine)

    def rebuild(self, engine: Engine) -> int:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM kb_fts"))
            conn.execute(
                text(
                    """
                    INSERT INTO kb_fts(rowid, content, user_id, document_id, chunk_id, seq)
                    SELECT id, content, user_id, document_id, id, seq FROM kb_chunks
                    """
                )
            )
            row = conn.execute(text("SELECT changes()")).scalar()
        return int(row or 0)

    def search(
        self,
        engine: Engine,
        user_id: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        fts_query = build_fts_query(query)
        if not fts_query:
            return []
        sql = text(
            """
            SELECT chunk_id, document_id, seq, snippet(kb_fts, 0, '<mark>', '</mark>', ' … ', 24) AS snippet
            FROM kb_fts
            WHERE kb_fts MATCH :q AND user_id = :uid
            ORDER BY rank
            LIMIT :limit
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(
                sql, {"q": fts_query, "uid": user_id, "limit": limit}
            ).fetchall()
        return [
            {
                "chunk_id": r[0],
                "document_id": r[1],
                "seq": r[2],
                "snippet": r[3] or "",
                "rank": idx,
            }
            for idx, r in enumerate(rows)
        ]


class PostgresFtsBackend(FtsBackend):
    """Postgres ``tsvector`` + GIN path (prod, phrase 4).

    Documented seam: the real implementation runs on a generated tsvector
    column + GIN index over the same fields. Kept import-guarded and behind
    the interface so dev never blocks on a live Postgres.
    """

    def ensure_schema(self, engine: Engine) -> None:  # pragma: no cover
        raise NotImplementedError("Postgres FTS backend ships with prod migrations")

    def rebuild(self, engine: Engine) -> int:  # pragma: no cover
        raise NotImplementedError("Postgres FTS backend ships with prod migrations")

    def search(
        self,
        engine: Engine,
        user_id: int,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError("Postgres FTS backend ships with prod migrations")


def _ensure_fts_ddl(engine: Engine) -> None:
    """Create the FTS5 table + sync triggers idempotently on ``engine``.

    Called by ``ensure_schema`` (startup) and lazily by ``ensure_fts_schema``
    so tests that swap in an in-memory engine still get a working index.
    """
    with engine.begin() as conn:
        # A stale kb_fts from an older schema (e.g. created before the seq
        # column was added) breaks triggers/queries. Detect and recreate it.
        cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(kb_fts)"))
        }
        # PRAGMA returns rows only when the table exists; an existing table
        # without the seq column is a stale schema → drop so it's recreated.
        if cols and "seq" not in cols:
            conn.execute(text("DROP TABLE kb_fts"))
        conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
                    content,
                    user_id UNINDEXED,
                    document_id UNINDEXED,
                    chunk_id UNINDEXED,
                    seq UNINDEXED,
                    tokenize='porter unicode61'
                )
                """
            )
        )
        # Idempotent sync triggers (phrase 3). Guarded by DROP-then-CREATE so
        # re-running startup never stacks duplicate triggers.
        for name in ("kb_fts_ai", "kb_fts_ad", "kb_fts_au"):
            conn.execute(text(f"DROP TRIGGER IF EXISTS {name}"))
        conn.execute(
            text(
                """
                CREATE TRIGGER kb_fts_ai AFTER INSERT ON kb_chunks BEGIN
                    INSERT INTO kb_fts(rowid, content, user_id, document_id, chunk_id, seq)
                    VALUES (new.id, new.content, new.user_id, new.document_id, new.id, new.seq);
                END
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER kb_fts_ad AFTER DELETE ON kb_chunks BEGIN
                    DELETE FROM kb_fts WHERE rowid = old.id;
                END
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TRIGGER kb_fts_au AFTER UPDATE ON kb_chunks BEGIN
                    DELETE FROM kb_fts WHERE rowid = old.id;
                    INSERT INTO kb_fts(rowid, content, user_id, document_id, chunk_id, seq)
                    VALUES (new.id, new.content, new.user_id, new.document_id, new.id, new.seq);
                END
                """
            )
        )


def get_fts_backend() -> FtsBackend:
    """Return the backend matching the configured database driver."""
    url = (settings.DATABASE_URL or "").lower()
    if url.startswith("postgres"):
        return PostgresFtsBackend()
    return SQLiteFtsBackend()


# --------------------------------------------------------------------------- #
# Query builder (phrase 5)
# --------------------------------------------------------------------------- #

def _escape_term(term: str) -> str:
    """Escape a bare term against FTS5 special chars."""
    return "".join("\\" + ch if ch in _FTS_SPECIAL else ch for ch in term)


def tokenize_query(query: str) -> list[str]:
    """Lowercase, strip punctuation, split into word tokens (phrase 5).

    Stopwords (``what``, ``is``, …) are dropped so natural-language questions
    don't AND-empty the index (Phase 3, Idea 24 typo-tolerance spirit).
    """
    words = re.findall(r"\w+", (query or "").lower())
    return [
        w
        for w in words
        if len(w) >= settings.KB_FTS_MIN_TOKEN and w not in STOPWORDS
    ]


def build_fts_query(query: str) -> str:
    """Translate a raw query into an FTS5 match expression.

    ``"phrase here"`` → quoted phrase; bare words → prefix-matched and
    AND-joined; handles AND/OR (uppercase) operators.
    """
    q = (query or "").strip()
    if not q:
        return ""

    # Preserve explicit quoted phrases first.
    tokens: list[str] = []
    pos = 0
    for m in _PHRASE_RE.finditer(q):
        before = q[pos : m.start()].strip()
        if before:
            tokens.extend(tokenize_query(before))
        phrase = m.group(1).strip()
        if phrase:
            tokens.append(f'"{_escape_term(phrase)}"')
        pos = m.end()
    tail = q[pos:].strip()
    if tail:
        tokens.extend(tokenize_query(tail))

    if not tokens:
        return ""

    expr_parts: list[str] = []
    for tok in tokens:
        if tok in ("AND", "OR"):
            expr_parts.append(tok)
            continue
        if tok.startswith('"'):
            expr_parts.append(tok)
        else:
            # Prefix match (phrase 5 / typo tolerance, Idea 24).
            expr_parts.append(f"{_escape_term(tok)}*")
    expr = " ".join(expr_parts)
    # A leading/trailing OR would be invalid FTS5.
    expr = re.sub(r"^OR\s+|OR$", "", expr).strip()
    return expr


# Engines that already ran the DDL — avoids dropping/recreating triggers on
# every search. Safe because SQLAlchemy engines are long-lived singletons.
_initialized_engines: set[int] = set()


def ensure_fts_schema(engine: Engine) -> None:
    """Idempotent startup hook: create the FTS index if enabled (phrase 2)."""
    if not settings.KB_FTS_ENABLED:
        return
    if id(engine) in _initialized_engines:
        return
    get_fts_backend().ensure_schema(engine)
    _initialized_engines.add(id(engine))


__all__ = [
    "FtsBackend",
    "SQLiteFtsBackend",
    "PostgresFtsBackend",
    "get_fts_backend",
    "build_fts_query",
    "tokenize_query",
    "ensure_fts_schema",
    "ensure_fts_schema_for",
]


def ensure_fts_schema_for(engine: Engine) -> None:
    """Ensure the FTS schema exists on the given engine, if enabled.

    Used by ``KbSearcher`` so retrieval self-heals when a session is bound to
    an engine (e.g. an in-memory test engine) that never ran the startup hook.
    Also reconciles drift: the FTS virtual table is *not* part of
    ``Base.metadata``, so test ``drop_all``/``create_all`` wipes ``kb_chunks``
    but leaves stale ``kb_fts`` rows behind (colliding rowids). A count check
    lets us rebuild cheaply whenever the two diverge.
    """
    if not settings.KB_FTS_ENABLED:
        return
    if id(engine) not in _initialized_engines:
        get_fts_backend().ensure_schema(engine)
        _initialized_engines.add(id(engine))
    _heal_drift(engine)


def _heal_drift(engine: Engine) -> None:
    """Reconcile the FTS index + triggers with ``kb_chunks``.

    Handles three divergences cheaply:
    - The sync trigger is missing (e.g. a ``drop_all``/``create_all`` in tests
      dropped ``kb_chunks`` and took its triggers with it) → re-run the DDL.
    - ``kb_chunks`` has rows but ``kb_fts`` is empty → full rebuild.
    - ``kb_fts`` has stale rows but ``kb_chunks`` is empty (table reset) → clear.
    """
    try:
        with engine.connect() as conn:
            trigger_ok = conn.execute(
                text(
                    "SELECT count(*) FROM sqlite_master "
                    "WHERE type='trigger' AND name='kb_fts_ai'"
                )
            ).scalar()
            fts_count = conn.execute(text("SELECT count(*) FROM kb_fts")).scalar() or 0
            chunk_count = (
                conn.execute(text("SELECT count(*) FROM kb_chunks")).scalar() or 0
            )
        if not trigger_ok:
            # The chunk table was reset (e.g. test drop_all), which dropped the
            # triggers AND orphaned stale kb_fts rows that will collide with
            # fresh chunk rowids. Re-create the DDL, then clear stale rows by
            # rebuilding from the (possibly empty) chunk table.
            _initialized_engines.discard(id(engine))
            get_fts_backend().ensure_schema(engine)
            get_fts_backend().rebuild(engine)
            _initialized_engines.add(id(engine))
            return
        if fts_count == 0 and chunk_count > 0:
            get_fts_backend().rebuild(engine)
        elif fts_count > 0 and chunk_count == 0:
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM kb_fts"))
    except Exception as exc:  # noqa: BLE001 — never fail retrieval on heal
        logger.warning("FTS drift heal skipped (%s)", exc)
