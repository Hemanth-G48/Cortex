"""Curriculum catalog CRUD router."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Institution, CurriculumCourse, CurriculumSubject, CurriculumUnit
from app.schemas.curriculum import (
    InstitutionCreate,
    InstitutionResponse,
    ProgramCreate,
    ProgramResponse,
    SubjectCreate,
    SubjectResponse,
    CurriculumCreate,
    CurriculumResponse,
)
from app.services.users import current_user

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


# ---------------------------------------------------------------------------
# Public: Institutions
# ---------------------------------------------------------------------------

@router.get("/institutions", response_model=List[InstitutionResponse])
def list_institutions(db: Session = Depends(get_db)):
    institutions = (
        db.query(Institution).filter(Institution.is_active == True).order_by(Institution.id).all()
    )
    return institutions


@router.get("/institutions/{institution_id}", response_model=InstitutionResponse)
def get_institution(institution_id: int, db: Session = Depends(get_db)):
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(404, "Institution not found")
    return institution


# ---------------------------------------------------------------------------
# Public: Programs under an institution (active only)
# ---------------------------------------------------------------------------

@router.get("/institutions/{institution_id}/programs", response_model=List[ProgramResponse])
def list_institution_programs(institution_id: int, db: Session = Depends(get_db)):
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(404, "Institution not found")
    return (
        db.query(CurriculumCourse)
        .filter(CurriculumCourse.institution_id == institution_id, CurriculumCourse.is_active == True)
        .order_by(CurriculumCourse.id)
        .all()
    )


@router.get("/programs/{program_id}", response_model=ProgramResponse)
def get_program(program_id: int, db: Session = Depends(get_db)):
    program = db.query(CurriculumCourse).filter(CurriculumCourse.id == program_id).first()
    if not program:
        raise HTTPException(404, "Program not found")
    return program


# ---------------------------------------------------------------------------
# Public: Subjects under a program
# ---------------------------------------------------------------------------

@router.get("/programs/{program_id}/subjects", response_model=List[SubjectResponse])
def list_program_subjects(program_id: int, db: Session = Depends(get_db)):
    program = db.query(CurriculumCourse).filter(CurriculumCourse.id == program_id).first()
    if not program:
        raise HTTPException(404, "Program not found")
    subjects = (
        db.query(CurriculumSubject)
        .filter(CurriculumSubject.program_id == program_id)
        .order_by(CurriculumSubject.semester, CurriculumSubject.id)
        .all()
    )
    result = []
    for subj in subjects:
        unit_count = (
            db.query(CurriculumUnit)
            .filter(CurriculumUnit.subject_id == subj.id)
            .count()
        )
        subj.unit_count = unit_count
        result.append(subj)
    return result


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")
    subject.unit_count = (
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id)
        .count()
    )
    return subject


# ---------------------------------------------------------------------------
# Public: Units under a subject
# ---------------------------------------------------------------------------

@router.get("/subjects/{subject_id}/units", response_model=List[CurriculumResponse])
def list_subject_units(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")
    return (
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id)
        .order_by(CurriculumUnit.unit_number)
        .all()
    )


# ---------------------------------------------------------------------------
# Public: Single unit (used by the frontend Unit page)
# ---------------------------------------------------------------------------

@router.get("/units/{unit_id}", response_model=CurriculumResponse)
def get_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = db.query(CurriculumUnit).filter(CurriculumUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(404, "Unit not found")
    return unit


# ---------------------------------------------------------------------------
# Admin: Institutions
# ---------------------------------------------------------------------------

@router.get("/institutions/admin/all", response_model=List[InstitutionResponse])
def list_all_institutions_admin(
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    return db.query(Institution).order_by(Institution.id).all()


@router.post("/institutions", response_model=InstitutionResponse)
def create_institution(
    data: InstitutionCreate,
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    institution = Institution(**data.model_dump())
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


@router.patch("/institutions/{institution_id}/status")
def toggle_institution_status(
    institution_id: int,
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(404, "Institution not found")
    institution.is_active = not institution.is_active
    db.commit()
    return {"ok": True, "is_active": institution.is_active}


# ---------------------------------------------------------------------------
# Admin: Programs under an institution
# ---------------------------------------------------------------------------

@router.post("/institutions/{institution_id}/programs", response_model=ProgramResponse)
def create_institution_program(
    institution_id: int,
    data: ProgramCreate,
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(404, "Institution not found")
    program = CurriculumCourse(institution_id=institution_id, **data.model_dump())
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


# ---------------------------------------------------------------------------
# Admin: Subjects under a program
# ---------------------------------------------------------------------------

@router.post("/programs/{program_id}/subjects", response_model=SubjectResponse)
def create_program_subject(
    program_id: int,
    data: SubjectCreate,
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    program = db.query(CurriculumCourse).filter(CurriculumCourse.id == program_id).first()
    if not program:
        raise HTTPException(404, "Program not found")
    subject = CurriculumSubject(program_id=program_id, **data.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    subject.unit_count = 0
    return subject


# ---------------------------------------------------------------------------
# Admin: Units under a subject
# ---------------------------------------------------------------------------

@router.post("/subjects/{subject_id}/units", response_model=CurriculumResponse)
def create_subject_unit(
    subject_id: int,
    data: CurriculumCreate,
    current_user = Depends(current_user),
    db: Session = Depends(get_db),
):
    subject = db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")
    unit = CurriculumUnit(subject_id=subject_id, **data.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit