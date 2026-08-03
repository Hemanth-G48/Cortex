from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScheduleEvent
from app.schemas.schedule_event import (
    ScheduleEventCreate,
    ScheduleEventUpdate,
    ScheduleEventResponse,
)

router = APIRouter(prefix="/api", tags=["schedule-events"])


@router.get("/schedule", response_model=List[ScheduleEventResponse])
def list_schedule_events(
    day_of_week: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(ScheduleEvent)
    if day_of_week is not None:
        query = query.filter(ScheduleEvent.day_of_week == day_of_week)
    return query.order_by(ScheduleEvent.day_of_week, ScheduleEvent.start_time).all()


@router.post("/schedule", response_model=ScheduleEventResponse)
def create_schedule_event(data: ScheduleEventCreate, db: Session = Depends(get_db)):
    event = ScheduleEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.put("/schedule/{event_id}", response_model=ScheduleEventResponse)
def update_schedule_event(event_id: int, data: ScheduleEventUpdate, db: Session = Depends(get_db)):
    event = db.query(ScheduleEvent).filter(ScheduleEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Schedule event not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(event, key, val)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/schedule/{event_id}")
def delete_schedule_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ScheduleEvent).filter(ScheduleEvent.id == event_id).first()
    if not event:
        raise HTTPException(404, "Schedule event not found")
    db.delete(event)
    db.commit()
    return {"ok": True}
