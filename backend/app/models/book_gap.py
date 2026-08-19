"""Book Knowledge Gap Analyzer models.

Three tables power the feature:

- ``BookGapAnalysis`` — one row per (user, book): the dashboard rollup
  (concept counts by status, recommended reading share) plus diagnostics.
- ``BookGapItem`` — one row per (book, concept): the concept's snapshot in
  that book — chapter/section/pages/snippet, the analysis classification
  (KNOWN / PARTIALLY_KNOWN / UNKNOWN), the user's learning progress
  (UNKNOWN → LEARNING → LEARNED → MASTERED), a 0-5 knowledge level,
  difficulty, estimated reading minutes, and historical/outdated flag.
- ``BookConceptState`` — the CUMULATIVE cross-book knowledge store: one row
  per (user, canonical concept). "Mark as learned" lands here and future
  analyses of other books treat it as strong evidence (cross-book dedup).
  It never writes to the Second Brain vault — the vault stays the primary
  evidence source; this is only the explicit override.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class BookGapAnalysis(Base):
    __tablename__ = "book_gap_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    # done | failed
    status = Column(String(20), default="done")
    total_pages = Column(Integer, default=0)
    chapters = Column(Integer, default=0)
    # Stage-1 TOC rollup: number of topics extracted from the table of contents.
    total_concepts = Column(Integer, default=0)
    known = Column(Integer, default=0)
    partial = Column(Integer, default=0)
    unknown = Column(Integer, default=0)
    # Stage-1 additional buckets.
    needs_review = Column(Integer, default=0)
    # Stage-2: how many topics have a persisted deep analysis.
    deep_analyzed = Column(Integer, default=0)
    historical = Column(Integer, default=0)
    # Pages the reader should actually study (unknown + partial spans).
    recommended_pages = Column(Integer, default=0)
    recommended_pct = Column(Float, default=0.0)
    errors_json = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_book_gap_user_book"),
    )


class BookGapTopic(Base):
    """One topic from a book's Table of Contents (chapter / section / subsection).

    Stage 1 (TOC analysis, deterministic, no LLM) writes one row per topic
    heading with its Second Brain match status. Stage 2 (deep topic-level
    analysis, explicit user action) fills the ``deep_*`` fields with the
    persisted result — opening the book or navigating never recomputes it.

    Statuses: KNOWN | PARTIALLY_KNOWN | UNKNOWN | NEEDS_REVIEW.
    Deep statuses: NOT_ANALYZED | ANALYZING | ANALYZED | FAILED.
    """

    __tablename__ = "book_gap_topics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    # Heading text + position in the book's hierarchy.
    title = Column(String(300), nullable=False)
    # 1 chapter · 2 section · 3 subsection.
    level = Column(Integer, default=1)
    # Chapter heading this topic lives under (None for chapters themselves).
    parent_title = Column(String(300), nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)

    # Stage 1 — TOC ↔ Second Brain match.
    # KNOWN | PARTIALLY_KNOWN | UNKNOWN | NEEDS_REVIEW.
    status = Column(String(20), default="UNKNOWN")
    # exact | normalized | alias | token | subset | none.
    match_source = Column(String(20), nullable=True)
    # Canonical vault concept name that matched (for KNOWN/PARTIAL display).
    second_brain_match = Column(String(200), nullable=True)
    # 0..1 confidence in the match (low → NEEDS_REVIEW, never false "known").
    confidence = Column(Float, default=0.0)

    # Stage 2 — deep topic-level analysis (persisted, explicit re-analyze only).
    # NOT_ANALYZED | ANALYZING | ANALYZED | FAILED.
    deep_status = Column(String(20), default="NOT_ANALYZED")
    deep_result_json = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "title", name="uq_book_topic_book_title"),
    )


class BookGapItem(Base):
    __tablename__ = "book_gap_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    # When this item came from a deep topic-level analysis, the originating
    # TOC topic (so the UI can show it under the right chapter/section).
    deep_topic_id = Column(Integer, nullable=True, index=True)
    # Canonical concept key (see concepts.canonicalize) + best display spelling.
    concept = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=False)
    chapter = Column(String(200), nullable=True)
    section = Column(String(200), nullable=True)
    # Page span this concept covers in the book (grouped, per requirement: a
    # concept spanning pages 342-351 is ONE item, not ten gaps).
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    snippet = Column(Text, nullable=True)
    why = Column(Text, nullable=True)
    # Analysis classification: KNOWN | PARTIALLY_KNOWN | UNKNOWN.
    status = Column(String(20), default="UNKNOWN")
    # User's learning progress: UNKNOWN | LEARNING | LEARNED | MASTERED.
    my_status = Column(String(20), default="UNKNOWN")
    # 0 Unknown … 5 Practical/mastery (requirement 13).
    knowledge_level = Column(Integer, default=0)
    difficulty = Column(String(20), default="Beginner")
    est_minutes = Column(Integer, default=0)
    # Potentially outdated/legacy material — preserved, never discarded.
    is_historical = Column(Boolean, default=False)
    historical_note = Column(String(500), nullable=True)
    # Set when my_status >= LEARNED: the book the user learned it from
    # (cross-book dedup: "already learned from Book C").
    learned_from_book_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "concept", name="uq_book_gap_book_concept"),
    )


class BookConceptState(Base):
    """Cumulative per-concept knowledge state across ALL books.

    One row per (user, canonical concept). ``my_status`` transitions
    UNKNOWN → LEARNING → LEARNED → MASTERED via the "mark as learned"
    actions; the analyzer treats LEARNED/MASTERED as strong evidence when
    analyzing any future book (cross-book deduplication).
    """

    __tablename__ = "book_concept_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept = Column(String(200), nullable=False)
    my_status = Column(String(20), default="UNKNOWN")
    learned_from_book_id = Column(Integer, nullable=True)
    page_ref = Column(Integer, nullable=True)
    updated_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "concept", name="uq_book_concept_user_concept"),
    )
