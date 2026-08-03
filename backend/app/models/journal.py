from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey

from app.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    mood = Column(String(50), nullable=True)
    tags = Column(String(500), nullable=True)
