from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Mood states the session-design mapping understands (kept in sync with
# app/models/mood_log.py; schemas stay model-free per project convention).
MOODS = ("stressed", "focused", "relaxed")


class MoodCreate(BaseModel):
    mood: str
    energy: int = Field(default=3, ge=1, le=5)
    note: Optional[str] = None

    @field_validator("mood")
    @classmethod
    def mood_must_be_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in MOODS:
            raise ValueError(f"mood must be one of {', '.join(MOODS)}")
        return v


class MoodResponse(BaseModel):
    id: int
    mood: str
    energy: int
    note: Optional[str] = None
    logged_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Analytics / insights payloads ───────────────────────────────────────── #

class MoodDistributionItem(BaseModel):
    mood: str
    count: int


class MoodAnalytics(BaseModel):
    total_entries: int
    avg_energy: Optional[float] = None
    dominant_mood: Optional[str] = None
    distribution: list[MoodDistributionItem]
    daily_trend: list[dict]  # [{date, avg_energy, mood}]


class MoodDailyPoint(BaseModel):
    date: date
    mood: Optional[str] = None
    energy: Optional[float] = None


class MoodWeekly(BaseModel):
    days: list[MoodDailyPoint]


class MoodInsight(BaseModel):
    date: date
    mood: Optional[str] = None
    energy: Optional[float] = None
    journal_snippet: Optional[str] = None
    daily_log_focus_minutes: Optional[int] = None


class SessionParams(BaseModel):
    mood: str
    focus_minutes: int
    break_type: str
    difficulty: str
    description: str
