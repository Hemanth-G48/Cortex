from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api", tags=["eisenhower"])

QUADRANTS = {
    "urgent_important": "Urgent/Important",
    "important_not_urgent": "Important/Not Urgent",
    "urgent_not_important": "Urgent/Not Important",
    "not_important": "Not Important/Not Urgent",
}


@router.get("/eisenhower/matrix")
def eisenhower_matrix(db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.status != "Completed").all()
    matrix = {key: [] for key in QUADRANTS}
    for t in tasks:
        # Default heuristic when a task has no explicit quadrant yet:
        # High priority → Urgent/Important; Medium → Important/Not Urgent;
        # Low → Not Important; None → Important/Not Urgent.
        quadrant = t.priority_quadrant
        if not quadrant:
            quadrant = {
                "High": "Urgent/Important",
                "Medium": "Important/Not Urgent",
                "Low": "Not Important/Not Urgent",
            }.get(t.priority_tag, "Important/Not Urgent")
        for key, value in QUADRANTS.items():
            if quadrant == value:
                matrix[key].append({
                    "id": t.id,
                    "title": t.title,
                    "subject_tag": t.subject_tag,
                    "priority_tag": t.priority_tag,
                    "priority_quadrant": quadrant,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "status": t.status,
                })
                break
    return matrix


@router.post("/eisenhower/tasks/{task_id}/complete", response_model=TaskResponse)
def complete_eisenhower_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.status = "Completed"
    db.commit()
    db.refresh(task)
    return task
