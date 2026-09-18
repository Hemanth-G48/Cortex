from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JournalEntry
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse

router = APIRouter(prefix="/api", tags=["journal"])


@router.get("/journal-entries", response_model=List[JournalEntryResponse])
def list_entries(db: Session = Depends(get_db)):
    return db.query(JournalEntry).order_by(JournalEntry.date.desc()).all()


@router.post("/journal-entries", response_model=JournalEntryResponse)
def create_entry(data: JournalEntryCreate, db: Session = Depends(get_db)):
    entry = JournalEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
def update_entry(entry_id: int, data: JournalEntryCreate, db: Session = Depends(get_db)):
    """Edit an existing journal entry (audit defect #20)."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    for key, val in data.model_dump().items():
        setattr(entry, key, val)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/journal-entries/{entry_id}")
def delete_journal_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(404, "Journal entry not found")
    db.delete(entry)
    db.commit()
    return {"ok": True}
