"""Fitness Hub dashboard endpoints (99-phase plan, Phase 39-40).

Composes the ``fitness_hub`` service helpers into a single summary payload
consumed by the FitnessHubDashboard page (sidebar widgets + 5 main rows).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.fitness_hub import fitness_hub_summary

router = APIRouter(prefix="/api", tags=["fitness-hub"])


@router.get("/fitness-hub/summary")
def get_fitness_hub_summary(db: Session = Depends(get_db)):
    """Phase 39: aggregated payload for the whole dashboard."""
    user = db.query(User).order_by(User.id).first()
    return fitness_hub_summary(db, user)
