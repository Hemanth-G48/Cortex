from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Course
from app.schemas.course import CourseCreate, CourseResponse

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _attach_progress(db: Session, courses: list[Course]) -> list[Course]:
    """Set transient progress_percentage from assignment completion.

    Progress is computed (done/total assignments per course) rather than
    trusting the stored current_assignment counters.
    """
    course_ids = [c.id for c in courses]
    rows = (
        db.query(Assignment.course_id)
        .filter(Assignment.course_id.in_(course_ids))
        .all()
    )
    total_by_course: dict[int, int] = {}
    for (cid,) in rows:
        total_by_course[cid] = total_by_course.get(cid, 0) + 1
    done_by_course: dict[int, int] = {}
    done_rows = (
        db.query(Assignment.course_id)
        .filter(Assignment.course_id.in_(course_ids), Assignment.status == "Completed")
        .all()
    )
    for (cid,) in done_rows:
        done_by_course[cid] = done_by_course.get(cid, 0) + 1

    for course in courses:
        total = total_by_course.get(course.id, 0)
        done = done_by_course.get(course.id, 0)
        course.progress_percentage = round(done / total * 100, 1) if total > 0 else 0.0
    return courses


@router.get("/", response_model=List[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    courses = db.query(Course).all()
    return _attach_progress(db, courses)


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    return _attach_progress(db, [course])[0]


@router.post("/", response_model=CourseResponse)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, data: CourseCreate, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    for key, val in data.model_dump().items():
        setattr(course, key, val)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    db.delete(course)
    db.commit()
    return {"ok": True}
