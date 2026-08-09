"""Tutor session + message models — rolling RAG chat history (Idea 61)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class TutorSession(Base):
    __tablename__ = "tutor_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("tutor_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # user | assistant
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    # JSON list of {chunk_id, document_id, title, source_path, snippet}
    sources = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
