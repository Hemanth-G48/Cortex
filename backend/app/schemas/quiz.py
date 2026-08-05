"""Pydantic schemas for quizzes and attempts."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class QuizCreate(BaseModel):
    unit_id: int
    num_questions: int = 10
    difficulty: str = "medium"


class QuizResponse(BaseModel):
    id: int
    unit_id: int
    questions: list[dict]
    difficulty: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QuizAttemptRequest(BaseModel):
    # `None` entries represent unanswered questions (skipped/out of range).
    answers: list[Optional[int]]


class QuizAttemptResult(BaseModel):
    score: int
    total: int
    percentage: float
    results: list[dict]
    # G13 (Phase 85): XP granted for a passing attempt (0 when none).
    xp_awarded: int = 0


class HistoryItem(BaseModel):
    id: int
    quiz_id: int
    answers: list[int]
    score: Optional[int]
    total_questions: Optional[int]
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
