from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, ForeignKey
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    created_date = Column(Date, nullable=False)
    # Notes editor (99-phase plan, Group 13)
    pinned = Column(Boolean, default=False)
    updated_at = Column(DateTime, nullable=True)


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    # Phase 10 (Idea 98): per-user scoping for the goal/reflection system.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    quarter = Column(String(10), nullable=False)  # Q1–Q4
    progress_percentage = Column(Float, default=0.0)
    year = Column(Integer, nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=True)
    target_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False)
    # Phase 10 (Idea 98, phrase 71): goal↔subject/roadmap linkage.
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=True, index=True)
    roadmap_id = Column(Integer, ForeignKey("roadmaps.id"), nullable=True)
