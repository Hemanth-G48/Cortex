"""MistakeAnalysis model — explain-my-mistake walkthroughs (Idea 68)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class MistakeAnalysis(Base):
    __tablename__ = "mistake_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("practice_questions.id"), nullable=False, index=True)
    student_answer = Column(Text, nullable=True)
    # The generated walkthrough (LLM or keyword-diff fallback).
    walkthrough = Column(Text, nullable=True)
    # JSON list of missed key points (strings).
    missed_points = Column(Text, nullable=True)
    # Recommended note to re-read (kb_chunks.id) + concept to review (kb_concepts.id).
    recommended_chunk_id = Column(Integer, nullable=True)
    recommended_concept_id = Column(Integer, nullable=True)
    # True when a RevisionSchedule entry was created (phrase 75).
    revision_task_created = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
