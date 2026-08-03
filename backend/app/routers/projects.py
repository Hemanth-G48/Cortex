from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, ProjectTask
from app.schemas.project import (
    ProjectCreate, ProjectResponse,
    ProjectTaskCreate, ProjectTaskResponse, ProjectTaskUpdate,
)

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@router.post("/projects", response_model=ProjectResponse)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    for key, val in data.model_dump().items():
        setattr(project, key, val)
    db.commit()
    db.refresh(project)
    return project


# Project Tasks
@router.get("/projects/{project_id}/tasks", response_model=List[ProjectTaskResponse])
def list_project_tasks(project_id: int, db: Session = Depends(get_db)):
    return db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()


@router.post("/project-tasks", response_model=ProjectTaskResponse)
def create_project_task(data: ProjectTaskCreate, db: Session = Depends(get_db)):
    task = ProjectTask(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/project-tasks/{task_id}", response_model=ProjectTaskResponse)
def update_project_task(task_id: int, data: ProjectTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Project task not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(task, key, val)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.delete("/project-tasks/{task_id}")
def delete_project_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(ProjectTask).filter(ProjectTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Project task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/summary")
def project_summary(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    total_tasks = len(tasks)
    incomplete_tasks = sum(1 for t in tasks if not t.completed)

    days_to_go = None
    if project.deadline:
        days_to_go = (project.deadline - date.today()).days

    if project.status == "Completed":
        deadline_status = "Completed"
    elif days_to_go is None:
        deadline_status = "No deadline"
    elif days_to_go < 0:
        deadline_status = "Overdue"
    elif days_to_go <= 7:
        deadline_status = "7 Days to go"
    else:
        deadline_status = f"{days_to_go} Days to go"

    return {
        "total_tasks": total_tasks,
        "incomplete_tasks": incomplete_tasks,
        "days_to_go": days_to_go,
        "deadline_status": deadline_status,
    }
