from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrainDumpCreate(BaseModel):
    content: Optional[str] = None


class BrainDumpResponse(BaseModel):
    id: int
    user_id: int
    content: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
