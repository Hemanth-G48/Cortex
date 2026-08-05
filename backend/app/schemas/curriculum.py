from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional


# ---------------------------------------------------------------------------
# Institution
# ---------------------------------------------------------------------------

class InstitutionBase(BaseModel):
    name: str
    short_name: str
    description: Optional[str] = None
    is_active: bool = False


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class InstitutionResponse(InstitutionBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Program (CurriculumCourse)
# ---------------------------------------------------------------------------

class ProgramCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    duration: int = 8


class ProgramResponse(ProgramCreate):
    id: int
    institution_id: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Subject (CurriculumSubject)
# ---------------------------------------------------------------------------

class SubjectCreate(BaseModel):
    name: str
    code: str
    semester: Optional[int] = None
    credits: int = 3
    description: Optional[str] = None


class SubjectResponse(SubjectCreate):
    id: int
    program_id: int
    is_active: bool
    unit_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# CurriculumUnit (CurriculumUnit)
# ---------------------------------------------------------------------------

class CurriculumCreate(BaseModel):
    unit_number: int
    name: str
    description: Optional[str] = None


class CurriculumResponse(CurriculumCreate):
    id: int
    subject_id: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
