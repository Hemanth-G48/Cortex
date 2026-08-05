"""Book model for the reading tracker (STUDENT-PLANAR G4)."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    author = Column(String(200), nullable=True)
    category = Column(String(20), default="want")  # reading | finished | want
    cover_url = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
