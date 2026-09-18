from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float, Date, Text
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    avatar = Column(String(255), nullable=True)
    avatar_class = Column(String(50), default="Wizard")
    current_level = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Fitness Hub (99-phase plan, Phases 1-2): weight-goal + membership
    current_weight = Column(Float, nullable=True)
    initial_weight = Column(Float, nullable=True)
    target_weight = Column(Float, nullable=True)
    membership_status = Column(String(50), default="Active")
    next_payment_date = Column(Date, nullable=True)

    # Role auth (STUDENT-PLANAR G1)
    username = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(20), default="student")

    # SyllabusAI (G1): local curator/admin flag (additive — the student/teacher
    # `role` from STUDENT-PLANAR is left untouched).
    is_admin = Column(Boolean, default=False)

    # Enrollment binding (Phase 13)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    program_id = Column(Integer, ForeignKey("curriculum_courses.id"), nullable=True)

    # Audit defect #96: JSON client preferences (AI model choice, etc.)
    # persisted server-side; single source of truth across devices.
    prefs_json = Column(Text, nullable=True)

    # Phase 5 (Idea 49, phrase 83): per-user pacing multiplier for time
    # estimates (default 1.0; learning_events will tune it later).
    pacing_multiplier = Column(Float, default=1.0)
