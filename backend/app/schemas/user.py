from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str
    avatar: Optional[str] = None
    avatar_class: str = "Wizard"
    current_level: int = 1
    current_streak: int = 0
    total_xp: int = 0
    # Fitness Hub (Phases 1-2)
    current_weight: Optional[float] = None
    initial_weight: Optional[float] = None
    target_weight: Optional[float] = None
    membership_status: str = "Active"
    next_payment_date: Optional[date] = None
    # Role auth (STUDENT-PLANAR G1)
    username: Optional[str] = None
    email: Optional[str] = None
    role: str = "student"
    # SyllabusAI (G1): local curator/admin flag.
    is_admin: bool = False
    # SyllabusAI (G2): curriculum enrollment binding.
    institution_id: Optional[int] = None
    program_id: Optional[int] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    avatar_class: Optional[str] = None
    current_level: Optional[int] = None
    current_streak: Optional[int] = None
    total_xp: Optional[int] = None
    current_weight: Optional[float] = None
    initial_weight: Optional[float] = None
    target_weight: Optional[float] = None
    membership_status: Optional[str] = None
    next_payment_date: Optional[date] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_admin: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserSignup(BaseModel):
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    password: str
    role: str = "student"
    teacher_secret: Optional[str] = None


class UserLogin(BaseModel):
    identifier: str
    password: str


class EnrollmentUpdate(BaseModel):
    institution_id: int
    program_id: int
