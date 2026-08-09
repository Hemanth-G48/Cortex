"""UserPreference model — learning-preference profile (Phase 8, Idea 71).

One row per user (unique ``user_id``). The profile drives prompt rendering
across the tutor and explanations: depth (overview vs deep-dive), a 0–1
``examples_vs_theory`` slider, verbosity style, preferred session length,
and the explanation register (plain / analogy / formal). ``onboarding_completed``
flags whether the first-run questionnaire has been finished.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, unique=True)
    # overview | deep_dive
    depth = Column(String(20), default="overview")
    # 0.0 = pure theory … 1.0 = examples-first.
    examples_vs_theory = Column(Float, default=0.5)
    # concise | detailed
    style = Column(String(20), default="concise")
    session_length_mins = Column(Integer, default=30)
    # plain | analogy | formal
    explanation_style = Column(String(20), default="plain")
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)
