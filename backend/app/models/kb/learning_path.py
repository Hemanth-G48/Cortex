"""Learning Path Planner — source-hierarchy models (Layer 1: the real platform).

The folder/entity model mirrors the *external platform's* structure — the
external website is the source of truth:

    Platform
      └── LearningPath            (one row per learning path discovered on the site)
            ├── section           (path page sections, e.g. "Common SSRF attacks")
            │     └── resource    (LearningResource — reading pages & labs)
            └── resources

``LearningResource`` rows are deduplicated per plan by URL via the
``LearningPathResource`` junction — one resource can appear in several
learning paths ("This resource is already completed" then updates every path
that contains it).

Every crawl is tracked honestly: ``crawl_status`` is one of
``discovered | crawled | extraction_failed | http_error | not_found |
auth_required`` and the verification fields (``requested_url``, ``final_url``,
``status_code``, ``error``) record what actually happened on the wire. Nothing
is ever marked ``crawled`` unless the request succeeded AND useful content was
extracted.

``LearningDependency`` persists prerequisite edges with their provenance:
``source == "platform"`` when the site explicitly states the prerequisite,
``source == "ai"`` when the AI inferred it (never presented as official).
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base

# Honest crawl states (never claim success for a failed request).
CRAWL_DISCOVERED = "discovered"
CRAWL_CRAWLED = "crawled"
CRAWL_EXTRACTION_FAILED = "extraction_failed"
CRAWL_HTTP_ERROR = "http_error"
CRAWL_NOT_FOUND = "not_found"
CRAWL_AUTH_REQUIRED = "auth_required"
CRAWL_AI_GENERATED = "ai_generated"
# Plan re-sync: the source index no longer lists this path (it was on the
# site when first discovered, but the re-crawl did not see it).
CRAWL_REMOVED = "removed"

CRAWL_STATUSES = {
    CRAWL_DISCOVERED,
    CRAWL_CRAWLED,
    CRAWL_EXTRACTION_FAILED,
    CRAWL_HTTP_ERROR,
    CRAWL_NOT_FOUND,
    CRAWL_AUTH_REQUIRED,
    CRAWL_AI_GENERATED,
    CRAWL_REMOVED,
}

# Resource types: reading material vs practical exercise.
RESOURCE_TYPE_READING = "reading"
RESOURCE_TYPE_LAB = "lab"

# Dependency provenance: the site said so vs the AI inferred it.
DEP_SOURCE_PLATFORM = "platform"
DEP_SOURCE_AI = "ai"


class LearningPath(Base):
    """A learning path discovered on an external platform (Layer 1)."""

    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False, index=True)
    # The platform this path belongs to (e.g. "PortSwigger Web Security Academy").
    platform = Column(String(120), nullable=False, default="")
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    # Difficulty exactly as the site labels it (e.g. "PRACTITIONER").
    difficulty = Column(String(60), nullable=True)
    # Exact URL discovered from the site ("View path" link) — never guessed.
    source_url = Column(String(600), nullable=False)
    # Exact "start here" URL the site exposes (may be auth-gated).
    first_resource_url = Column(String(600), nullable=True)
    # Total resources the site reports (the "0 of 23" counter).
    resource_total = Column(Integer, nullable=True)
    # Rows extracted from the path page.
    section_count = Column(Integer, nullable=True)
    resource_count = Column(Integer, nullable=True)
    # Honest crawl state + verification trail.
    crawl_status = Column(String(24), default=CRAWL_DISCOVERED, index=True)
    final_url = Column(String(600), nullable=True)
    status_code = Column(Integer, nullable=True)
    error = Column(String(300), nullable=True)
    crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class LearningResource(Base):
    """One resource (reading page or lab) inside a learning path.

    Deduplicated per plan by URL: a resource that appears in several paths is
    one row linked to each path through ``LearningPathResource``.
    """

    __tablename__ = "learning_resources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    # Exact URL discovered from the site (None when the public page did not
    # expose one — the site gates it behind sign-in).
    url = Column(String(600), nullable=True)
    # reading | lab
    resource_type = Column(String(20), default=RESOURCE_TYPE_READING)
    difficulty = Column(String(60), nullable=True)
    # The path section this resource sits in (e.g. "Common SSRF attacks").
    section = Column(String(200), nullable=True)
    # Display order within the path page.
    sort_order = Column(Integer, default=0)
    # Normalized dedup key (host + path, query stripped).
    url_key = Column(String(600), nullable=True, index=True)
    # Honest crawl state + verification trail.
    crawl_status = Column(String(24), default=CRAWL_DISCOVERED, index=True)
    requested_url = Column(String(600), nullable=True)
    final_url = Column(String(600), nullable=True)
    status_code = Column(Integer, nullable=True)
    error = Column(String(300), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class LearningPathResource(Base):
    """Junction: which learning paths contain which (deduplicated) resources."""

    __tablename__ = "learning_path_resources"
    __table_args__ = (UniqueConstraint("path_id", "resource_id", name="uq_path_resource"),)

    id = Column(Integer, primary_key=True, index=True)
    path_id = Column(Integer, ForeignKey("learning_paths.id"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("learning_resources.id"), nullable=False, index=True)
    # Section + order are per-path (the same resource may sit in different
    # sections of different paths).
    section = Column(String(200), nullable=True)
    sort_order = Column(Integer, default=0)


class LearningDependency(Base):
    """Prerequisite edge with provenance (platform-stated vs AI-inferred)."""

    __tablename__ = "learning_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False, index=True)
    from_label = Column(String(300), nullable=False)
    to_label = Column(String(300), nullable=False)
    from_url = Column(String(600), nullable=True)
    to_url = Column(String(600), nullable=True)
    # platform | ai
    source = Column(String(20), default=DEP_SOURCE_AI)
    # Human-facing note ("Recommended prerequisite" vs "Official prerequisite").
    note = Column(String(300), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class PortswiggerSession(Base):
    """Stored PortSwigger sign-in for the Learning Path Planner.

    PortSwigger gates the deep learning-path resource URLs behind a sign-in
    wall, so this row keeps the user's own session (cookies) plus — when they
    asked to remember it — the credentials needed to refresh an expired
    session. Single-user local app: the password is only *obfuscated*
    (base64, NOT encryption), never logged, and never returned by the API.
    The cookies are the reusable part: the crawler uses them to fetch the
    sign-in-gated URLs and to extract the hrefs public pages hide.
    """

    __tablename__ = "portswigger_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    # Base64-obfuscated credentials (only set when the user chose "remember").
    password_obfuscated = Column(Text, nullable=True)
    # Session cookies (name → value) for the portswigger.net domain.
    cookies_json = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
