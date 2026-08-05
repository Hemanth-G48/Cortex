from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_hhmm(v: str) -> str:
    try:
        h, m = v.split(":")
        hh, mm = int(h), int(m)
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError("time must be in HH:MM 24h format")  # noqa: B904
    return f"{hh:02d}:{mm:02d}"


class SleepCreate(BaseModel):
    date: date
    bedtime: str
    wake_time: str
    quality: int = Field(default=3, ge=1, le=5)
    notes: Optional[str] = None

    @field_validator("bedtime", "wake_time")
    @classmethod
    def times(cls, v: str) -> str:
        return _validate_hhmm(v)


class SleepUpdate(BaseModel):
    bedtime: Optional[str] = None
    wake_time: Optional[str] = None
    quality: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None

    @field_validator("bedtime", "wake_time")
    @classmethod
    def times(cls, v: Optional[str]) -> Optional[str]:
        return _validate_hhmm(v) if v else v


class SleepResponse(BaseModel):
    id: int
    date: date
    bedtime: str
    wake_time: str
    quality: int
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Analytics / recommendations payloads ────────────────────────────────── #

class SleepAnalytics(BaseModel):
    nights_logged: int
    avg_hours: Optional[float] = None
    consistency_hours: Optional[float] = None  # stddev of hours
    deviation_hours: Optional[float] = None    # avg - target
    nights_under_target: int = 0
    target_hours: float


class SleepDayPoint(BaseModel):
    date: date
    hours: Optional[float] = None
    quality: Optional[int] = None


class SleepSummary(BaseModel):
    target_hours: float
    last_night: Optional[SleepDayPoint] = None
    week: list[SleepDayPoint]
    avg_hours: Optional[float] = None
    nights_under_target: int = 0


class SleepRecommendation(BaseModel):
    target_hours: float
    wake_time: str
    recommended_bedtime: Optional[str] = None
    alert: Optional[str] = None
    tips: list[str]
    schedule_hints: list[str]
