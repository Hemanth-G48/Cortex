from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Exam
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    ExamCreate,
    ExamResponse,
)

router = APIRouter(prefix="/api", tags=["assignments"])


# -- Assignments --
@router.get("/assignments", response_model=List[AssignmentResponse])
def list_assignments(db: Session = Depends(get_db)):
    return db.query(Assignment).all()


@router.get("/courses/{course_id}/assignments", response_model=List[AssignmentResponse])
def list_course_assignments(course_id: int, db: Session = Depends(get_db)):
    return db.query(Assignment).filter(Assignment.course_id == course_id).all()


@router.post("/assignments", response_model=AssignmentResponse)
def create_assignment(data: AssignmentCreate, db: Session = Depends(get_db)):
    assignment = Assignment(**data.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(assignment_id: int, data: AssignmentCreate, db: Session = Depends(get_db)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    for key, val in data.model_dump().items():
        setattr(assignment, key, val)
    db.commit()
    db.refresh(assignment)
    return assignment


# -- Exams --
@router.get("/exams", response_model=List[ExamResponse])
def list_exams(db: Session = Depends(get_db)):
    return db.query(Exam).all()


@router.get("/courses/{course_id}/exams", response_model=List[ExamResponse])
def list_course_exams(course_id: int, db: Session = Depends(get_db)):
    return db.query(Exam).filter(Exam.course_id == course_id).all()


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"ok": True}


@router.delete("/exams/{exam_id}")
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    db.delete(exam)
    db.commit()
    return {"ok": True}


@router.post("/exams", response_model=ExamResponse)
def create_exam(data: ExamCreate, db: Session = Depends(get_db)):
    exam = Exam(**data.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam
