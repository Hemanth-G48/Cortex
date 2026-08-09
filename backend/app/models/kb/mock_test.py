"""Mock test models — exam simulations (Idea 64).

``MockTest`` stores the assembled paper (section structure + question ids);
``MockTestAttempt`` captures one timed run with per-topic analytics.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class MockTest(Base):
    __tablename__ = "mock_tests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    # JSON: {sections: [{title, question_ids: []}], questions: [{id, topic_id}]}
    structure_json = Column(Text, nullable=True)
    duration_mins = Column(Integer, default=60)
    # draft | active | completed (phrase 31).
    status = Column(String(10), default="draft", index=True)
    created_at = Column(DateTime, server_default=func.now())


class MockTestAttempt(Base):
    __tablename__ = "mock_test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mock_test_id = Column(Integer, ForeignKey("mock_tests.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
    # JSON: {question_id: selected_option_text}
    answers = Column(Text, nullable=True)
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    # JSON: {topic_id: {correct, total}}
    per_topic = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
