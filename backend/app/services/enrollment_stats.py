"""Enrollment progress analytics for SyllabusAI (G12)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    User,
    Institution,
    CurriculumCourse,
    CurriculumSubject,
    CurriculumUnit,
    Material,
    Quiz,
    QuizAttempt,
)


def enrollment_summary(db: Session, user: User) -> dict:
    """Aggregate progress for the user's enrolled institution/program.

    Safe for unenrolled users: returns zero/None values without erroring.
    """
    institution = None
    program = None
    subjects: list[dict] = []
    units: list[dict] = []
    subject_ids: list[int] = []
    unit_ids: list[int] = []

    if user.institution_id:
        institution = (
            db.query(Institution).filter(Institution.id == user.institution_id).first()
        )
    if user.program_id:
        program = (
            db.query(CurriculumCourse)
            .filter(CurriculumCourse.id == user.program_id)
            .first()
        )

    if program is not None:
        subj_rows = (
            db.query(CurriculumSubject)
            .filter(CurriculumSubject.program_id == program.id)
            .order_by(CurriculumSubject.semester, CurriculumSubject.id)
            .all()
        )
        for s in subj_rows:
            unit_count = (
                db.query(CurriculumUnit)
                .filter(CurriculumUnit.subject_id == s.id)
                .count()
            )
            subjects.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "code": s.code,
                    "semester": s.semester,
                    "credits": s.credits,
                    "unit_count": unit_count,
                }
            )
            subject_ids.append(s.id)

        if subject_ids:
            unit_rows = (
                db.query(CurriculumUnit)
                .filter(CurriculumUnit.subject_id.in_(subject_ids))
                .order_by(CurriculumUnit.subject_id, CurriculumUnit.unit_number)
                .all()
            )
            for u in unit_rows:
                units.append(
                    {
                        "id": u.id,
                        "name": u.name,
                        "unit_number": u.unit_number,
                        "subject_id": u.subject_id,
                    }
                )
                unit_ids.append(u.id)

    # Materials in the enrolled program's units.
    material_count = 0
    uploaded_materials = 0
    if unit_ids:
        material_count = (
            db.query(Material)
            .filter(Material.unit_id.in_(unit_ids), Material.is_active == True)  # noqa: E712
            .count()
        )
        uploaded_materials = (
            db.query(Material)
            .filter(
                Material.unit_id.in_(unit_ids),
                Material.uploaded_by_id == user.id,
                Material.is_active == True,  # noqa: E712
            )
            .count()
        )

    # Quiz attempts scoped to the enrolled program's units.
    quiz_attempts = 0
    avg_quiz_percentage: float | None = None
    quiz_ids: list[int] = []
    if unit_ids:
        quiz_ids = [
            q.id for q in db.query(Quiz.id).filter(Quiz.unit_id.in_(unit_ids)).all()
        ]
    if quiz_ids:
        attempts = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.user_id == user.id,
                QuizAttempt.quiz_id.in_(quiz_ids),
            )
            .all()
        )
        quiz_attempts = len(attempts)
        scored = [a for a in attempts if a.score is not None and a.total_questions]
        if scored:
            avg_quiz_percentage = round(
                sum((a.score / a.total_questions) * 100 for a in scored) / len(scored),
                1,
            )

    return {
        "institution_id": user.institution_id,
        "program_id": user.program_id,
        "institution_name": institution.name if institution else None,
        "program_name": program.name if program else None,
        "subjects": subjects,
        "units": units,
        "material_count": material_count,
        "quiz_attempts": quiz_attempts,
        "avg_quiz_percentage": avg_quiz_percentage,
        "uploaded_materials": uploaded_materials,
    }
