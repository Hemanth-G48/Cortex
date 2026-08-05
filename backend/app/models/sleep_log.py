from sqlalchemy import Column, Date, Integer, String, Text

from app.database import Base


class SleepLog(Base):
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    date = Column(Date, nullable=False, index=True)
    # Stored as "HH:MM" 24h strings (SQLite has no native time column and the
    # existing app stores ScheduleEvent times as strings too).
    bedtime = Column(String(5), nullable=False)   # e.g. "23:00"
    wake_time = Column(String(5), nullable=False)  # e.g. "07:00"
    quality = Column(Integer, nullable=False, default=3)  # 1..5
    notes = Column(Text, nullable=True)
