from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=dict)
def login(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return {"user": None}
    return {
        "user": UserResponse.model_validate(user).model_dump()
    }
