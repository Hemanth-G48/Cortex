from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Quest, QuestTask, User
from app.schemas.quest import (
    QuestCreate, QuestResponse,
    QuestTaskCreate, QuestTaskResponse,
)

router = APIRouter(prefix="/api", tags=["quests"])


@router.get("/quests", response_model=List[QuestResponse])
def list_quests(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Quest)
    if status:
        query = query.filter(Quest.status == status)
    if priority:
        query = query.filter(Quest.priority == priority)
    if category:
        query = query.filter(Quest.category == category)
    return query.all()


@router.post("/quests", response_model=QuestResponse)
def create_quest(data: QuestCreate, db: Session = Depends(get_db)):
    quest = Quest(**data.model_dump())
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return quest


@router.put("/quests/{quest_id}", response_model=QuestResponse)
def update_quest(quest_id: int, data: QuestCreate, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(404, "Quest not found")
    for key, val in data.model_dump().items():
        setattr(quest, key, val)
    db.commit()
    db.refresh(quest)
    return quest


@router.post("/quests/{quest_id}/complete", response_model=QuestResponse)
def complete_quest(quest_id: int, db: Session = Depends(get_db)):
    from datetime import date
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(404, "Quest not found")
    quest.status = "Completed"
    # Award XP to the shared wallet: character XP (levels + reward affordability)
    # and the user's total_xp mirror so the quest-centre wallet stays consistent.
    char = db.query(Character).filter(Character.user_id == quest.user_id).first()
    if char:
        char.xp += quest.xp_reward
        new_level = (char.xp // 1000) + 1
        if new_level > char.level:
            char.level = new_level
    user = db.query(User).filter(User.id == quest.user_id).first()
    if user:
        user.total_xp = (user.total_xp or 0) + quest.xp_reward
    # Streak: reset to 1 if the last completion was more than a day ago,
    # otherwise increment (Phase 18).
    user = db.query(User).filter(User.id == quest.user_id).first()
    if user:
        last_done = (
            db.query(Quest)
            .filter(Quest.user_id == quest.user_id, Quest.status == "Completed", Quest.id != quest_id)
            .order_by(Quest.updated_at.desc())
            .first()
        )
        last_date = last_done.updated_at.date() if (last_done and last_done.updated_at) else None
        today = date.today()
        if last_date is None or (today - last_date).days > 1:
            user.current_streak = 1
        else:
            user.current_streak = (user.current_streak or 0) + 1
    db.commit()
    db.refresh(quest)
    return quest


# Quest Tasks
@router.get("/quests/{quest_id}/tasks", response_model=List[QuestTaskResponse])
def list_quest_tasks(quest_id: int, db: Session = Depends(get_db)):
    return db.query(QuestTask).filter(QuestTask.quest_id == quest_id).all()


@router.post("/quest-tasks", response_model=QuestTaskResponse)
def create_quest_task(data: QuestTaskCreate, db: Session = Depends(get_db)):
    task = QuestTask(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.put("/quest-tasks/{task_id}", response_model=QuestTaskResponse)
def update_quest_task(task_id: int, data: QuestTaskCreate, db: Session = Depends(get_db)):
    task = db.query(QuestTask).filter(QuestTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Quest task not found")
    for key, val in data.model_dump().items():
        setattr(task, key, val)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/quests/{quest_id}")
def delete_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(404, "Quest not found")
    db.delete(quest)
    db.commit()
    return {"ok": True}


@router.delete("/quest-tasks/{task_id}")
def delete_quest_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(QuestTask).filter(QuestTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Quest task not found")
    db.delete(task)
    db.commit()
    return {"ok": True}
