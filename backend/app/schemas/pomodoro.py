from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PomodoroSessionBase(BaseModel):
    start_time: datetime
    duration_minutes: int
    completed: bool = False
    task_description: Optional[str] = None
    # Gamified Habit Tracker (Phase 6)
    mode: str = "Focus"  # Focus / Break


class PomodoroSessionCreate(PomodoroSessionBase):
    user_id: int


class PomodoroSessionResponse(PomodoroSessionBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
