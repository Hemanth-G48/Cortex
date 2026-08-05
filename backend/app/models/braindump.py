"""BrainDump model (STUDENT-PLANAR G6).

A single free-text quick-capture note per user — one row per user (enforced by
the ``unique`` constraint on ``user_id``), upserted with debounced autosave.
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func

from app.database import Base


class BrainDump(Base):
    __tablename__ = "braindumps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
