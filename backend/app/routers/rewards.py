from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Reward, User
from app.schemas.reward import (
    RewardCreate,
    RewardUpdate,
    RewardResponse,
    ClaimRewardResponse,
)

router = APIRouter(prefix="/api", tags=["rewards"])


@router.get("/rewards", response_model=List[RewardResponse])
def list_rewards(
    available: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Reward)
    if available is not None:
        query = query.filter(Reward.is_available == available)
    return query.all()


@router.post("/rewards", response_model=RewardResponse)
def create_reward(data: RewardCreate, db: Session = Depends(get_db)):
    reward = Reward(**data.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.put("/rewards/{reward_id}", response_model=RewardResponse)
def update_reward(reward_id: int, data: RewardUpdate, db: Session = Depends(get_db)):
    reward = db.query(Reward).filter(Reward.id == reward_id).first()
    if not reward:
        raise HTTPException(404, "Reward not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(reward, key, val)
    db.commit()
    db.refresh(reward)
    return reward


@router.delete("/rewards/{reward_id}")
def delete_reward(reward_id: int, db: Session = Depends(get_db)):
    reward = db.query(Reward).filter(Reward.id == reward_id).first()
    if not reward:
        raise HTTPException(404, "Reward not found")
    db.delete(reward)
    db.commit()
    return {"ok": True}


@router.post("/rewards/{reward_id}/claim", response_model=ClaimRewardResponse)
def claim_reward(reward_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    reward = db.query(Reward).filter(Reward.id == reward_id).first()
    if not reward:
        raise HTTPException(404, "Reward not found")
    if reward.claimed_date:
        raise HTTPException(400, "Reward already claimed")

    char = db.query(Character).filter(Character.user_id == user_id).first()
    if not char:
        raise HTTPException(404, "Character not found")
    if char.xp < reward.xp_cost:
        raise HTTPException(400, f"Not enough XP. Need {reward.xp_cost}, have {char.xp}")

    # Shared wallet: deduct from both the character and the user so habit XP,
    # quest XP and reward spends all draw from the same pool (Phase 24).
    char.xp -= reward.xp_cost
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.total_xp = max((user.total_xp or 0) - reward.xp_cost, 0)
    reward.claimed_date = datetime.now(timezone.utc)
    reward.is_available = False
    db.commit()
    db.refresh(reward)

    return ClaimRewardResponse(
        reward_id=reward.id,
        title=reward.title,
        xp_cost=reward.xp_cost,
        xp_remaining=char.xp,
        claimed_at=reward.claimed_date,
    )


@router.get("/rewards/claimed", response_model=List[RewardResponse])
def list_claimed_rewards(db: Session = Depends(get_db)):
    return db.query(Reward).filter(Reward.claimed_date.isnot(None)).all()
