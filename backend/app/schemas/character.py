from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CharacterBase(BaseModel):
    name: str
    class_name: str = "Wizard"
    level: int = 1
    xp: int = 0
    strength: int = 5
    agility: int = 5
    intelligence: int = 5
    endurance: int = 5
    current_quests: int = 0


class CharacterCreate(CharacterBase):
    user_id: int


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    class_name: Optional[str] = None
    level: Optional[int] = None
    xp: Optional[int] = None
    strength: Optional[int] = None
    agility: Optional[int] = None
    intelligence: Optional[int] = None
    endurance: Optional[int] = None
    current_quests: Optional[int] = None


class CharacterResponse(CharacterBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AddXpRequest(BaseModel):
    amount: int
