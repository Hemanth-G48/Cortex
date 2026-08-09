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
    # Phase 4 (Idea 40, phrase 93): the draft KbDocument this dump upserts
    # (None until the first save with content).
    linked_document_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
