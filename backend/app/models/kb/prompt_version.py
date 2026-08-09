"""PromptVersion model — versioned prompt templates (Idea 100, phrase 96).

Prompts become A/B-able: a ``(feature, version)`` row pins the template text a
given surface used. ``is_active`` marks the current version; the observability
report can compare feedback/faithfulness across versions.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    # tutor | explain | grading | agents | reflection | forecast
    feature = Column(String(30), nullable=False, index=True)
    version = Column(Integer, default=1)
    template = Column(Text, nullable=False)
    is_active = Column(Integer, default=1)  # SQLite bool
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("feature", "version", name="uq_prompt_versions_feature_version"),
    )
