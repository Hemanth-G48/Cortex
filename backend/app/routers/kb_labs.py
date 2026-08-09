"""Phase 6 labs router (Idea 55).

CRUD per user; ``GET /labs/{id}/prep`` returns the top vault chunks for each
pre-requisite topic as \"read before lab\" reading; completion logs a ``lab``
LearningEvent into the mastery/progress spine.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lab, Topic, User
from app.services.kb import KbService
from app.services.kb.mastery import log_event
from app.services.kb.search import KbSearcher
from app.services.security import get_current_user

router = APIRouter(prefix="/api", tags=["kb-labs"])

VALID_STATUS = ("scheduled", "done", "missed")


class LabCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=2, max_length=200)
    lab_date: date | None = None
    pre_requisite_topic_ids: list[int] = []
    notes: str | None = None
    submission_url: str | None = None


class LabUpdate(BaseModel):
    title: str | None = None
    lab_date: date | None = None
    pre_requisite_topic_ids: list[int] | None = None
    notes: str | None = None
    submission_url: str | None = None
    status: str | None = None


def _lab_or_404(db: Session, user_id: int, lab_id: int) -> Lab:
    lab = db.query(Lab).get(lab_id)
    if lab is None or lab.user_id != user_id:
        raise HTTPException(404, "Lab not found")
    return lab


def _lab_dict(db: Session, lab: Lab) -> dict:
    return {
        "id": lab.id,
        "subject_id": lab.subject_id,
        "title": lab.title,
        "lab_date": lab.lab_date.isoformat() if lab.lab_date else None,
        "status": lab.status,
        "pre_requisite_topic_ids": KbService.json_loads(lab.pre_requisite_topic_ids) or [],
        "notes": lab.notes,
        "submission_url": lab.submission_url,
    }


@router.get("/subjects/{subject_id}/labs")
def list_labs(
    subject_id: int,
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Lab).filter(Lab.user_id == current_user.id, Lab.subject_id == subject_id)
    if status:
        q = q.filter(Lab.status == status)
    return {"items": [_lab_dict(db, l) for l in q.order_by(Lab.lab_date.asc()).all()]}


@router.get("/labs")
def list_all_labs(
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Lab).filter(Lab.user_id == current_user.id)
    if status:
        q = q.filter(Lab.status == status)
    return {"items": [_lab_dict(db, l) for l in q.order_by(Lab.lab_date.asc()).all()]}


@router.post("/subjects/{subject_id}/labs", status_code=201)
def create_lab(
    subject_id: int,
    body: LabCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lab = Lab(
        user_id=current_user.id,
        subject_id=subject_id,
        title=body.title,
        lab_date=body.lab_date,
        status="scheduled",
        pre_requisite_topic_ids=KbService.json_dumps(body.pre_requisite_topic_ids),
        notes=body.notes,
        submission_url=body.submission_url,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return _lab_dict(db, lab)


@router.put("/labs/{lab_id}")
def update_lab(
    lab_id: int,
    body: LabUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lab = _lab_or_404(db, current_user.id, lab_id)
    if body.status is not None and body.status not in VALID_STATUS:
        raise HTTPException(400, "Invalid status")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "pre_requisite_topic_ids" and value is not None:
            setattr(lab, field, KbService.json_dumps(value))
        else:
            setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return _lab_dict(db, lab)


@router.post("/labs/{lab_id}/complete")
def complete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lab = _lab_or_404(db, current_user.id, lab_id)
    lab.status = "done"
    # Log a learning event for mastery + progress (phrase 45).
    for tid in KbService.json_loads(lab.pre_requisite_topic_ids) or []:
        log_event(db, current_user.id, event_type="lab", topic_id=int(tid), value=1.0)
    db.commit()
    db.refresh(lab)
    return _lab_dict(db, lab)


@router.delete("/labs/{lab_id}")
def delete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lab = _lab_or_404(db, current_user.id, lab_id)
    db.delete(lab)
    db.commit()
    return {"ok": True}


@router.get("/labs/{lab_id}/prep")
def lab_prep(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """\"Read before lab\" — top chunks per pre-requisite topic (phrase 44)."""
    lab = _lab_or_404(db, current_user.id, lab_id)
    topic_ids = KbService.json_loads(lab.pre_requisite_topic_ids) or []
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == current_user.id, Topic.id.in_(topic_ids))
        .all()
        if topic_ids
        else []
    )
    searcher = KbSearcher(db, current_user.id)
    reading: list[dict] = []
    for t in topics:
        try:
            result = searcher.search(t.name, mode="hybrid", limit=2)
            items = result.get("items") or []
        except Exception:  # noqa: BLE001 — prep must degrade gracefully
            items = []
        reading.append(
            {
                "topic_id": t.id,
                "topic_name": t.name,
                "chunks": [
                    {
                        "chunk_id": c.get("chunk_id"),
                        "document_id": c.get("document_id"),
                        "title": c.get("title"),
                        "snippet": c.get("snippet"),
                    }
                    for c in items
                ],
            }
        )
    return {"lab_id": lab.id, "reading": reading}
