"""Daily schedule router: CRUD for date-specific schedule blocks."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyScheduleItem, User
from app.schemas.daily_schedule import (
    DailyScheduleItemCreate,
    DailyScheduleItemResponse,
    DailyScheduleItemUpdate,
    DailyScheduleStats,
)
from app.services.schedule_catalog import (
    CATEGORY_CLASS,
    ENERGY_CLASS,
    parse_time_range,
    validate_blocks,
)
from app.services.users import current_user

router = APIRouter(prefix="/api/dailyschedule", tags=["daily-schedule"])


def _get_item_or_404(db: Session, item_id: int, user_id: int) -> DailyScheduleItem:
    item = db.query(DailyScheduleItem).filter(DailyScheduleItem.id == item_id).first()
    if item is None or item.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule item not found")
    return item


@router.get("", response_model=list[DailyScheduleItemResponse])
def list_schedule(
    date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    items = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == current_user.id, DailyScheduleItem.date == date)
        .order_by(DailyScheduleItem.time_range)
        .all()
    )
    return items


@router.post("", response_model=DailyScheduleItemResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: DailyScheduleItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    parsed = parse_time_range(data.time_range)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time_range format. Use HH:MM-HH:MM (24h).",
        )

    existing = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == current_user.id, DailyScheduleItem.date == data.date)
        .all()
    )
    if validate_blocks(existing, parsed[0], parsed[1]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Overlapping schedule block",
        )

    item = DailyScheduleItem(
        user_id=current_user.id,
        date=data.date,
        time_range=data.time_range,
        activity=data.activity,
        category=data.category,
        cat_class=data.cat_class or CATEGORY_CLASS.get(data.category),
        location=data.location,
        energy=data.energy,
        e_class=data.e_class or ENERGY_CLASS.get(data.energy),
        notes=data.notes,
        done=data.done,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=DailyScheduleItemResponse)
def update_schedule(
    item_id: int,
    data: DailyScheduleItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    item = _get_item_or_404(db, item_id, current_user.id)

    new_time_range = data.time_range if data.time_range is not None else item.time_range
    if data.time_range is not None:
        parsed = parse_time_range(data.time_range)
        if parsed is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time_range format. Use HH:MM-HH:MM (24h).",
            )
        other_items = (
            db.query(DailyScheduleItem)
            .filter(
                DailyScheduleItem.user_id == current_user.id,
                DailyScheduleItem.date == item.date,
                DailyScheduleItem.id != item_id,
            )
            .all()
        )
        if validate_blocks(other_items, parsed[0], parsed[1]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Overlapping schedule block",
            )

    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(item, key, val)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", response_model=dict)
def delete_schedule(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    item = _get_item_or_404(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/{item_id}/toggle", response_model=DailyScheduleItemResponse)
def toggle_schedule(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    item = _get_item_or_404(db, item_id, current_user.id)
    item.done = not item.done
    db.commit()
    db.refresh(item)
    return item


@router.get("/stats", response_model=DailyScheduleStats)
def schedule_stats(
    date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
):
    items = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == current_user.id, DailyScheduleItem.date == date)
        .all()
    )
    total = len(items)
    done = sum(1 for i in items if i.done)
    ratio = round(done / total, 2) if total > 0 else 0.0
    return DailyScheduleStats(date=date, total=total, done=done, ratio=ratio)
