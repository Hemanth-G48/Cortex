"""KbTag model — a knowledge tag (inline or auto-generated) (Idea 1)."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class KbTag(Base):
    __tablename__ = "kb_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    # inline (parsed from content) | auto (generated)
    kind = Column(String(10), default="inline")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_kb_tags_user_name"),
    )
