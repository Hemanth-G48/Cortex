from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "Not started"
    deadline: Optional[date] = None


class ProjectCreate(ProjectBase):
    user_id: int


class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class ProjectTaskBase(BaseModel):
    project_id: int
    title: str
    completed: bool = False


class ProjectTaskCreate(ProjectTaskBase):
    pass


class ProjectTaskUpdate(BaseModel):
    """Partial updates for project tasks (all fields optional)."""
    project_id: Optional[int] = None
    title: Optional[str] = None
    completed: Optional[bool] = None


class ProjectTaskResponse(ProjectTaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
