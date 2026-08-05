from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class GoogleToken(Base):
    """Stored Google OAuth token (single-user app → one row, id=1)."""

    __tablename__ = "google_tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String(500), nullable=False, default="")
    refresh_token = Column(String(500), nullable=True)
    token_type = Column(String(50), default="Bearer")
    expires_in = Column(Integer, default=3600)
    acquired_at = Column(DateTime, server_default=func.now())
    scope = Column(String(1000), default="")
    email = Column(String(200), nullable=True)
