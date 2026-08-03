from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, User
from app.schemas.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    AddXpRequest,
)

router = APIRouter(prefix="/api", tags=["characters"])


@router.get("/characters/{user_id}", response_model=CharacterResponse)
def get_character(user_id: int, db: Session = Depends(get_db)):
    char = db.query(Character).filter(Character.user_id == user_id).first()
    if not char:
        raise HTTPException(404, "Character not found")
    return char


@router.post("/characters", response_model=CharacterResponse)
def create_character(data: CharacterCreate, db: Session = Depends(get_db)):
    char = Character(**data.model_dump())
    db.add(char)
    db.commit()
    db.refresh(char)
    return char


@router.put("/characters/{user_id}", response_model=CharacterResponse)
def update_character(user_id: int, data: CharacterUpdate, db: Session = Depends(get_db)):
    char = db.query(Character).filter(Character.user_id == user_id).first()
    if not char:
        raise HTTPException(404, "Character not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(char, key, val)
    db.commit()
    db.refresh(char)
    return char


@router.post("/characters/{user_id}/xp", response_model=CharacterResponse)
def add_xp(user_id: int, data: AddXpRequest, db: Session = Depends(get_db)):
    char = db.query(Character).filter(Character.user_id == user_id).first()
    if not char:
        raise HTTPException(404, "Character not found")
    char.xp += data.amount
    # Level-up: every 1000 XP = 1 level
    new_level = (char.xp // 1000) + 1
    if new_level > char.level:
        char.level = new_level
    # Shared wallet: also credit the user's total_xp so reward claims and the
    # quest-centre wallet read the same pool (see rewards.claim_reward).
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.total_xp = (user.total_xp or 0) + data.amount
    db.commit()
    db.refresh(char)
    return char


@router.get("/characters/{user_id}/stats", response_model=CharacterResponse)
def get_character_stats(user_id: int, db: Session = Depends(get_db)):
    char = db.query(Character).filter(Character.user_id == user_id).first()
    if not char:
        raise HTTPException(404, "Character not found")
    return char
