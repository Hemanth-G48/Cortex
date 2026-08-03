from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LifeArea, Goal
from app.schemas.life_area import LifeAreaCreate, LifeAreaUpdate, LifeAreaResponse
from app.schemas.note import GoalResponse

router = APIRouter(prefix="/api", tags=["life-areas"])


@router.get("/life-areas", response_model=List[LifeAreaResponse])
def list_life_areas(db: Session = Depends(get_db)):
    return db.query(LifeArea).all()


@router.post("/life-areas", response_model=LifeAreaResponse)
def create_life_area(data: LifeAreaCreate, db: Session = Depends(get_db)):
    area = LifeArea(**data.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.put("/life-areas/{area_id}", response_model=LifeAreaResponse)
def update_life_area(area_id: int, data: LifeAreaUpdate, db: Session = Depends(get_db)):
    area = db.query(LifeArea).filter(LifeArea.id == area_id).first()
    if not area:
        raise HTTPException(404, "Life area not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(area, key, val)
    db.commit()
    db.refresh(area)
    return area


@router.delete("/life-areas/{area_id}")
def delete_life_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(LifeArea).filter(LifeArea.id == area_id).first()
    if not area:
        raise HTTPException(404, "Life area not found")
    db.delete(area)
    db.commit()
    return {"ok": True}


@router.get("/life-areas/{area_id}/goals", response_model=List[GoalResponse])
def life_area_goals(area_id: int, db: Session = Depends(get_db)):
    """Goals filtered by life area. Goals have no direct life_area FK, so they
    are matched by the goal title referencing the area name, or returned empty."""
    area = db.query(LifeArea).filter(LifeArea.id == area_id).first()
    if not area:
        raise HTTPException(404, "Life area not found")
    goals = db.query(Goal).all()
    name_key = area.name.lower()
    return [g for g in goals if name_key in g.title.lower()]


@router.post("/life-areas/{area_id}/complete", response_model=LifeAreaResponse)
def complete_life_area(area_id: int, db: Session = Depends(get_db)):
    """Flip a life-area status to Completed and pin progress at 100 (Phase 19)."""
    area = db.query(LifeArea).filter(LifeArea.id == area_id).first()
    if not area:
        raise HTTPException(404, "Life area not found")
    area.status = "Completed"
    area.progress_percent = 100.0
    db.commit()
    db.refresh(area)
    return area
