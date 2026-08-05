"""Pydantic schemas for summaries."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SummaryResponse(BaseModel):
    id: int
    unit_ids: list[int]
    content: str
    key_points: list[str]
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SummaryGenerateRequest(BaseModel):
    unit_ids: list[int]


class SummaryListItem(BaseModel):
    id: int
    unit_ids: list[int]
    content: str
    key_points: list[str]
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
