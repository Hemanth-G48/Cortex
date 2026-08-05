from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    category: str = "want"  # reading | finished | want
    cover_url: Optional[str] = None
    file_url: Optional[str] = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    cover_url: Optional[str] = None
    file_url: Optional[str] = None


class BookResponse(BookBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookInsights(BaseModel):
    total: int = 0
    finished: int = 0
    reading: int = 0
    want: int = 0
    completion_pct: float = 0.0
    per_author: dict[str, int] = {}
    added_this_month: int = 0
