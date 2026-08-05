"""Summary model for AI-generated unit summaries."""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, func, UniqueConstraint
from app.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=True, unique=True, index=True)
    unit_ids = Column(JSON, nullable=False, default=list)
    content = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("key", name="uq_summary_key"),
    )
