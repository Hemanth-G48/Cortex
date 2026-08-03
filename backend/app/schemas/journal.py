from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JournalEntryBase(BaseModel):
    date: date
    content: str
    mood: Optional[str] = None
    tags: Optional[str] = None


class JournalEntryCreate(JournalEntryBase):
    user_id: int


class JournalEntryResponse(JournalEntryBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
