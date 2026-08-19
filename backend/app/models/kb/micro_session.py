"""MicroSession model — concrete focus sessions (Phase 6, Idea 60).

A micro-session is a specific topic + a specific vault chunk + a practice task
for 15–45 minutes. Status: suggested → started → done. Completion logs a
``session`` LearningEvent (value = minutes).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class MicroSession(Base):
    __tablename__ = "micro_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    chunk_id = Column(Integer, ForeignKey("kb_chunks.id"), nullable=True)
    # Study-Session Loop (workflow): optional link to a learning-plan task.
    # A session can be tied to either a curriculum topic (legacy) or a
    # learning-plan task — never both, but the columns stay independent so
    # links survive even if the other side is deleted.
    learning_plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=True, index=True)
    learning_task_id = Column(Integer, ForeignKey("learning_tasks.id"), nullable=True, index=True)
    practice_task = Column(Text, nullable=True)
    duration_mins = Column(Integer, default=25)
    # suggested | started | done
    status = Column(String(20), default="suggested", index=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
