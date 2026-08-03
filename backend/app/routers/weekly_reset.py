from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Quest, User

router = APIRouter(prefix="/api", tags=["weekly-reset"])

WEEKLY_QUESTS = [
    {"title": "Complete 5 Daily Quests", "description": "Finish 5 daily quests this week", "xp_reward": 150, "category": "Weekly"},
    {"title": "Log 4 Focus Sessions", "description": "Complete 4 pomodoro sessions", "xp_reward": 120, "category": "Weekly"},
    {"title": "Review Weekly Goals", "description": "Set and review your goals for next week", "xp_reward": 100, "category": "Weekly"},
]


@router.post("/weekly-reset", response_model=dict)
def weekly_reset(db: Session = Depends(get_db)):
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    next_week_monday = monday + timedelta(days=7)

    existing = db.query(Quest).filter(
        Quest.due_date == monday,
        Quest.category == "Weekly"
    ).first()

    if existing:
        return {"message": "Weekly quests already exist for this week", "quests_created": False}

    created_count = 0
    for q_data in WEEKLY_QUESTS:
        quest = Quest(
            user_id=1,
            title=q_data["title"],
            description=q_data["description"],
            xp_reward=q_data["xp_reward"],
            status="Not started",
            due_date=next_week_monday,
            category="Weekly",
            priority="High",
            time_estimate=60,
        )
        db.add(quest)
        created_count += 1

    characters = db.query(Character).all()
    streak_bonus_count = 0
    for char in characters:
        completed_quests = db.query(Quest).filter(
            Quest.user_id == char.user_id,
            Quest.status == "Completed",
        ).count()
        if completed_quests >= 5:
            streak_bonus = completed_quests * 10
            char.xp += streak_bonus
            user = db.query(User).filter(User.id == char.user_id).first()
            if user:
                user.total_xp = (user.total_xp or 0) + streak_bonus
            streak_bonus_count += 1

    db.commit()
    return {
        "message": f"Weekly reset complete: {created_count} quests created",
        "quests_created": created_count,
        "streak_bonuses_awarded": streak_bonus_count,
    }
