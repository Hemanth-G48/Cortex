from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Assignment, Exam, User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentStatusUpdate,
    ExamCreate,
    ExamResponse,
)
from app.schemas.study_stats import AssignmentAnalyticsResponse
from app.services.security import get_current_user
from app.services.study_stats import compute_assignment_analytics
from app.services.kb.assignment_intel import plan_assignment
import uuid
from pathlib import Path

router = APIRouter(prefix="/api", tags=["assignments"])


# -- Assignments --
@router.get("/assignments/analytics", response_model=AssignmentAnalyticsResponse)
def assignment_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return compute_assignment_analytics(db, current_user.id)


@router.get("/assignments", response_model=List[AssignmentResponse])
def list_assignments(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    course_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Assignment)
    if type is not None:
        query = query.filter(Assignment.type == type)
    if status is not None:
        query = query.filter(Assignment.status == status)
    if course_id is not None:
        query = query.filter(Assignment.course_id == course_id)
    return query.all()


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


@router.post("/assignments/{assignment_id}/status", response_model=AssignmentResponse)
def update_assignment_status(
    assignment_id: int,
    data: AssignmentStatusUpdate,
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if data.status not in {"Not started", "In progress", "Completed"}:
        raise HTTPException(400, detail={"error": "Invalid status"})
    assignment.status = data.status
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/complete", response_model=AssignmentResponse)
def complete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    assignment.status = "Completed"
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/attachment", response_model=AssignmentResponse)
def upload_assignment_attachment(
    assignment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(400, detail={"error": "File type not allowed"})

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, detail={"error": "File too large"})

    directory = Path(settings.UPLOAD_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = directory / stored_name
    with target.open("wb") as out:
        out.write(data)

    assignment.file_url = f"/uploads/{stored_name}"
    db.commit()
    db.refresh(assignment)
    return assignment


# -- Phase 6 (Idea 54): assignment intelligence --
class PlanAssignmentRequest(BaseModel):
    create_tasks: bool = True
    create_reminders: bool = True


@router.post("/assignments/{assignment_id}/plan")
def plan_assignment_endpoint(
    assignment_id: int,
    body: PlanAssignmentRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """LLM subtask breakdown + task/reminder creation + hint chunks.

    Additive — the existing assignments flow is untouched (phrase 40).
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    body = body or PlanAssignmentRequest()
    result = plan_assignment(
        db,
        current_user.id,
        assignment,
        create_tasks=body.create_tasks,
        create_reminders=body.create_reminders,
    )
    db.commit()
    return result


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
