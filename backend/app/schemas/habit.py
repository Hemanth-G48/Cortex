from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HabitBase(BaseModel):
    name: str
    description: Optional[str] = None
    frequency: str = "daily"
    target_count: int = 1
    current_streak: int = 0
    longest_streak: int = 0
    color_theme: str = "blue"  # blue / green / orange / red
    is_archived: bool = False
    # Gamified Habit Tracker (Phases 1-3)
    habit_type: str = "good"  # good / bad
    xp_reward: int = 30
    xp_penalty: int = 20
    image_url: Optional[str] = None
    days_caught: int = 0
    # Fitness Hub (Phase 3)
    goal: Optional[str] = None
    heatmap_data: Optional[str] = None


class HabitCreate(HabitBase):
    user_id: int


class HabitResponse(HabitBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class HabitLogBase(BaseModel):
    habit_id: int
    date: date
    completed: bool = False
    count: int = 1
    # Gamified Habit Tracker (Phase 4)
    type: str = "good"  # good / bad
    status: str = "Completed"  # Completed / Shit I did it
    xp_change: int = 0
    # Phase 91: drag-and-drop sort within a calendar day column
    sort_order: int = 0


class HabitLogReorder(BaseModel):
    """New visual order of log ids within a calendar day (Phase 91)."""
    log_ids: list[int]


class HabitLogCreate(HabitLogBase):
    pass


class HabitLogUpdate(BaseModel):
    """Partial updates for habit logs (all fields optional).

    Editing a log (e.g. toggling ``completed`` or bumping ``count``) must NOT
    silently reset ``type``/``status``/``xp_change`` to their defaults, so the
    update endpoint applies only the fields the client actually sent.
    """
    habit_id: Optional[int] = None
    date: Optional[date] = None
    completed: Optional[bool] = None
    count: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None
    xp_change: Optional[int] = None
    sort_order: Optional[int] = None


class HabitLogResponse(HabitLogBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
