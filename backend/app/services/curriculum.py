"""Curriculum catalog query helpers used by the router."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Institution,
    CurriculumCourse,
    CurriculumSubject,
    CurriculumUnit,
)


def list_active_institutions(db: Session) -> list[Institution]:
    return db.query(Institution).filter(Institution.is_active == True).order_by(Institution.id).all()


def get_institution(db: Session, institution_id: int) -> Institution | None:
    return db.query(Institution).filter(Institution.id == institution_id).first()


def list_programs(db: Session, institution_id: int) -> list[CurriculumCourse]:
    return (
        db.query(CurriculumCourse)
        .filter(CurriculumCourse.institution_id == institution_id, CurriculumCourse.is_active == True)
        .order_by(CurriculumCourse.id)
        .all()
    )


def get_program(db: Session, program_id: int) -> CurriculumCourse | None:
    return db.query(CurriculumCourse).filter(CurriculumCourse.id == program_id).first()


def semester_label(semester: int | None, label: str | None) -> str | None:
    """Display label for a subject's semester (audit defect #9).

    Prefers the stored ``semester_label`` (editable per subject); falls back to
    formatting the numeric ``semester`` so pre-existing rows keep rendering the
    same text the UI used to build locally. Returns ``None`` when the subject
    carries no semester information at all.
    """
    cleaned = (label or "").strip()
    if cleaned:
        return cleaned
    if semester is not None:
        return f"Semester {semester}"
    return None


def list_subjects(db: Session, program_id: int) -> list[CurriculumSubject]:
    return (
        db.query(CurriculumSubject)
        .filter(CurriculumSubject.program_id == program_id)
        .order_by(CurriculumSubject.semester, CurriculumSubject.id)
        .all()
    )


def get_subject(db: Session, subject_id: int) -> CurriculumSubject | None:
    return db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()


def get_subject_with_unit_count(db: Session, subject_id: int) -> CurriculumSubject | None:
    subject = db.query(CurriculumSubject).filter(CurriculumSubject.id == subject_id).first()
    if subject is None:
        return None
    subject.unit_count = (
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id)
        .count()
    )
    return subject


def list_units(db: Session, subject_id: int) -> list[CurriculumUnit]:
    return (
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id)
        .order_by(CurriculumUnit.unit_number)
        .all()
    )
