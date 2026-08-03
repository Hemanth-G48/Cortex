from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Quest
from app.schemas.quest import QuestResponse

router = APIRouter(prefix="/api", tags=["daily-quests"])

DEFAULT_DAILY_QUESTS = [
    {"title": "Morning Review", "description": "Review yesterday's progress", "xp_reward": 30, "category": "Personal"},
    {"title": "Complete 3 Tasks", "description": "Finish at least 3 tasks from your todo list", "xp_reward": 50, "category": "Work"},
    {"title": "30 Min Focus Session", "description": "Complete one uninterrupted focus session", "xp_reward": 40, "category": "Personal"},
]


@router.get("/daily-quests", response_model=List[QuestResponse])
def get_or_create_daily_quests(db: Session = Depends(get_db)):
    today = date.today()
    existing = db.query(Quest).filter(Quest.due_date == today, Quest.category.in_(["Daily"])).all()
    if existing:
        return existing

    created = []
    for i, q in enumerate(DEFAULT_DAILY_QUESTS):
        quest = Quest(
            user_id=1,
            title=q["title"],
            description=q["description"],
            xp_reward=q["xp_reward"],
            status="Not started",
            due_date=today,
            category="Daily",
            priority="Medium",
            time_estimate=30,
        )
        db.add(quest)
        db.flush()
        created.append(quest)
    db.commit()
    for q in created:
        db.refresh(q)
    return created
