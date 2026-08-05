"""Grades / GPA router.

CRUD for ``Grade`` + ``CourseWeight`` rows plus computation endpoints backed
by ``services.grade_calc`` (port of Shiori's grade math).
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, CourseWeight, Grade
from app.schemas.grade import (
    CourseWeightCreate,
    CourseWeightResponse,
    CourseWeightUpdate,
    GPACourse,
    GPAResponse,
    GradeCalculateRequest,
    GradeCalculateResponse,
    GradeCreate,
    GradeResponse,
    NeededOnFinalRequest,
    NeededOnFinalResponse,
)
from app.services import grade_calc

router = APIRouter(prefix="/api/grades", tags=["grades"])


# ---------------------------------------------------------------------------
# Grade CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=List[GradeResponse])
def list_grades(db: Session = Depends(get_db)):
    return db.query(Grade).order_by(Grade.id).all()


@router.get("/courses/{course_id}", response_model=List[GradeResponse])
def list_course_grades(course_id: int, db: Session = Depends(get_db)):
    if not db.query(Course).filter(Course.id == course_id).first():
        raise HTTPException(404, "Course not found")
    return db.query(Grade).filter(Grade.course_id == course_id).order_by(Grade.id).all()


@router.post("", response_model=GradeResponse)
def create_grade(data: GradeCreate, db: Session = Depends(get_db)):
    grade = Grade(**data.model_dump())
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade


@router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(grade_id: int, data: GradeCreate, db: Session = Depends(get_db)):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(404, "Grade not found")
    for key, val in data.model_dump().items():
        setattr(grade, key, val)
    db.commit()
    db.refresh(grade)
    return grade


@router.delete("/{grade_id}")
def delete_grade(grade_id: int, db: Session = Depends(get_db)):
    grade = db.query(Grade).filter(Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(404, "Grade not found")
    db.delete(grade)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# CourseWeight CRUD
# ---------------------------------------------------------------------------

@router.get("/courses/{course_id}/weights", response_model=List[CourseWeightResponse])
def list_course_weights(course_id: int, db: Session = Depends(get_db)):
    return db.query(CourseWeight).filter(CourseWeight.course_id == course_id).order_by(CourseWeight.id).all()


@router.post("/weights", response_model=CourseWeightResponse)
def create_weight(data: CourseWeightCreate, db: Session = Depends(get_db)):
    weight = CourseWeight(**data.model_dump())
    db.add(weight)
    db.commit()
    db.refresh(weight)
    return weight


@router.put("/weights/{weight_id}", response_model=CourseWeightResponse)
def update_weight(weight_id: int, data: CourseWeightUpdate, db: Session = Depends(get_db)):
    weight = db.query(CourseWeight).filter(CourseWeight.id == weight_id).first()
    if not weight:
        raise HTTPException(404, "CourseWeight not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(weight, key, val)
    db.commit()
    db.refresh(weight)
    return weight


@router.delete("/weights/{weight_id}")
def delete_weight(weight_id: int, db: Session = Depends(get_db)):
    weight = db.query(CourseWeight).filter(CourseWeight.id == weight_id).first()
    if not weight:
        raise HTTPException(404, "CourseWeight not found")
    db.delete(weight)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=GradeCalculateResponse)
def calculate_course(data: GradeCalculateRequest, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")

    grades = db.query(Grade).filter(Grade.course_id == data.course_id).all()
    weights = db.query(CourseWeight).filter(CourseWeight.course_id == data.course_id).all()

    result = grade_calc.calculate_course_grade(
        [
            {"points_earned": g.points_earned, "points_possible": g.points_possible, "category_id": g.category_id}
            for g in grades
        ],
        [{"id": w.id, "weight": w.weight} for w in weights],
    )
    if result is None:
        return GradeCalculateResponse(course_id=data.course_id, grade_count=len(grades))
    return GradeCalculateResponse(
        course_id=data.course_id,
        percentage=result["percentage"],
        letter_grade=result["letter_grade"],
        is_weighted=result["is_weighted"],
        total_earned=result["total_earned"],
        total_possible=result["total_possible"],
        grade_count=len(grades),
    )


@router.get("/gpa", response_model=GPAResponse)
def cumulative_gpa(db: Session = Depends(get_db)):
    courses = db.query(Course).all()
    course_gpas: list[GPACourse] = []
    pairs: list[tuple[float, int]] = []

    for course in courses:
        grades = db.query(Grade).filter(Grade.course_id == course.id).all()
        weights = db.query(CourseWeight).filter(CourseWeight.course_id == course.id).all()
        result = grade_calc.calculate_course_grade(
            [
                {"points_earned": g.points_earned, "points_possible": g.points_possible, "category_id": g.category_id}
                for g in grades
            ],
            [{"id": w.id, "weight": w.weight} for w in weights],
        )
        entry = GPACourse(
            course_id=course.id,
            title=course.title,
            credits=course.credits or 3,
            percentage=result["percentage"] if result else None,
            letter_grade=result["letter_grade"] if result else None,
            gpa=grade_calc.pct_to_gpa(result["percentage"]) if result and result["percentage"] is not None else None,
        )
        course_gpas.append(entry)
        if result and result["percentage"] is not None:
            pairs.append((result["percentage"], course.credits or 3))

    return GPAResponse(gpa=grade_calc.cumulative_gpa(pairs), courses=course_gpas)


@router.post("/needed-on-final", response_model=NeededOnFinalResponse)
def needed_on_final(data: NeededOnFinalRequest) -> NeededOnFinalResponse:
    return NeededOnFinalResponse(needed_pct=grade_calc.needed_on_final(data.current_pct, data.final_weight_pct, data.desired_pct))
