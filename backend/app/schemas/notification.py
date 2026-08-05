from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationCreate(BaseModel):
    kind: str = "broadcast"
    title: str
    body: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    kind: str
    title: str
    body: Optional[str] = None
    ref_type: Optional[str] = None
    ref_id: Optional[int] = None
    read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCount(BaseModel):
    unread: int
