"""TopicDependency — topic→topic prerequisite edges (Phase 5, Idea 46).

``kb_edges`` requires a document source, so topic→topic dependencies get their
own small table. ``provenance``: ai (LLM seed) | rule (fallback) | manual
(user curated). Edges are cycle-checked on insert (phrase 55).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func

from app.database import Base


class TopicDependency(Base):
    __tablename__ = "topic_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    # prereq must be studied before postreq: prereq → postreq
    prereq_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    postreq_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    weight = Column(Float, default=1.0)
    # ai | rule | manual
    provenance = Column(String(10), default="ai")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id", "prereq_topic_id", "postreq_topic_id",
            name="uq_topic_dep_pair",
        ),
    )
