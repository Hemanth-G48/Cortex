"""Pydantic schemas for SyllabusAI materials."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialBase(BaseModel):
    unit_id: int
    title: str
    description: str | None = None
    file_type: str
    file_url: str
    file_size: int
    original_file_name: str


class MaterialCreate(MaterialBase):
    uploaded_by_id: int | None = None


class MaterialResponse(MaterialBase):
    id: int
    view_count: int
    download_count: int
    is_active: bool
    extracted_text: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
