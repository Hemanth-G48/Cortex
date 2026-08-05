from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class FlashcardBase(BaseModel):
    front: str
    back: str
    difficulty: str = "basic"
    streak: int = 0
    next_review: Optional[datetime] = None


class FlashcardCreate(FlashcardBase):
    pass


class FlashcardUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    difficulty: Optional[str] = None
    streak: Optional[int] = None
    next_review: Optional[datetime] = None


class FlashcardResponse(FlashcardBase):
    id: int
    deck_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FlashcardDeckBase(BaseModel):
    name: str
    course_id: Optional[int] = None


class FlashcardDeckCreate(FlashcardDeckBase):
    pass


class FlashcardDeckUpdate(BaseModel):
    name: Optional[str] = None
    course_id: Optional[int] = None


class FlashcardDeckResponse(FlashcardDeckBase):
    id: int
    created_at: Optional[datetime] = None
    cards: list[FlashcardResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FlashcardDeckSummary(FlashcardDeckBase):
    id: int
    created_at: Optional[datetime] = None
    card_count: int = 0

    model_config = ConfigDict(from_attributes=True)
