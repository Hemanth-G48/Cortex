from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Mission, MissionTask, Quest, User
from app.schemas.mission import (
    MissionCreate,
    MissionUpdate,
    MissionResponse,
    MissionTaskCreate,
    MissionTaskUpdate,
    MissionTaskResponse,
)
from app.schemas.quest import QuestResponse
from app.services.kb.mission_tasks import vault_task_suggestions
from app.services.users import current_user

router = APIRouter(prefix="/api", tags=["missions"])


@router.get("/missions", response_model=List[MissionResponse])
def list_missions(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Mission)
    if status:
        query = query.filter(Mission.status == status)
    if priority:
        query = query.filter(Mission.priority == priority)
    return query.all()


@router.post("/missions", response_model=MissionResponse)
def create_mission(data: MissionCreate, db: Session = Depends(get_db)):
    mission = Mission(**data.model_dump())
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


@router.put("/missions/{mission_id}", response_model=MissionResponse)
def update_mission(mission_id: int, data: MissionUpdate, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "Mission not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(mission, key, val)
    db.commit()
    db.refresh(mission)
    return mission


@router.delete("/missions/{mission_id}")
def delete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "Mission not found")
    db.delete(mission)
    db.commit()
    return {"ok": True}


@router.post("/missions/{mission_id}/complete", response_model=MissionResponse)
def complete_mission(mission_id: int, db: Session = Depends(get_db)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "Mission not found")
    mission.status = "Completed"
    char = db.query(Character).filter(Character.user_id == mission.user_id).first()
    if char:
        char.xp += mission.xp_reward
        new_level = (char.xp // 1000) + 1
        if new_level > char.level:
            char.level = new_level
    user = db.query(User).filter(User.id == mission.user_id).first()
    if user:
        user.total_xp = (user.total_xp or 0) + mission.xp_reward
    db.commit()
    db.refresh(mission)
    return mission


@router.get("/missions/{mission_id}/linked", response_model=List[QuestResponse])
def mission_linked_quests(mission_id: int, db: Session = Depends(get_db)):
    """Resolve a mission's comma-separated ``linked_quests`` ids to Quest rows (Phase 20)."""
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "Mission not found")
    if not mission.linked_quests:
        return []
    ids = [int(x) for x in mission.linked_quests.split(",") if x.strip().isdigit()]
    if not ids:
        return []
    return db.query(Quest).filter(Quest.id.in_(ids)).all()


# Mission Tasks
@router.get("/missions/{mission_id}/vault-tasks")
def list_vault_task_suggestions(
    mission_id: int,
    limit: int = Query(8, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Vault-derived subtask suggestions for a mission (audit defect #80).

    Search the Second Brain for the mission title, then mine the matching
    documents' checklist items / outline for actionable subtasks. Read-only —
    the client creates a real ``MissionTask`` only when the user accepts one.
    """
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "Mission not found")
    return vault_task_suggestions(db, user.id, mission.title, limit=limit)


@router.get("/missions/{mission_id}/tasks", response_model=List[MissionTaskResponse])
def list_mission_tasks(mission_id: int, db: Session = Depends(get_db)):
    return db.query(MissionTask).filter(MissionTask.mission_id == mission_id).all()


@router.post("/missions/{mission_id}/tasks", response_model=MissionTaskResponse)
def create_mission_task(mission_id: int, data: MissionTaskCreate, db: Session = Depends(get_db)):
    task = MissionTask(mission_id=mission_id, **data.model_dump(exclude={"mission_id"}))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/mission-tasks/{task_id}", response_model=MissionTaskResponse)
def update_mission_task(task_id: int, data: MissionTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(MissionTask).filter(MissionTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Mission task not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(task, key, val)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/mission-tasks/{task_id}")
def delete_mission_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(MissionTask).filter(MissionTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Mission task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}
