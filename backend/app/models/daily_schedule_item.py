"""DailyScheduleItem model (STUDENT-PLANAR G8).

Date-specific schedule blocks (a day view with energy/category/done), which
complement — not replace — the weekly-recurring ``ScheduleEvent`` table.
"""

from sqlalchemy import Column, Integer, String, Date, Text, Boolean, DateTime, ForeignKey, func

from app.database import Base


class DailyScheduleItem(Base):
    __tablename__ = "daily_schedule_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    time_range = Column(String(30), nullable=False)  # e.g. "08:00-09:30"
    activity = Column(String(200), nullable=False)
    category = Column(String(30), default="Study Time")  # School | Study Time | Break
    cat_class = Column(String(50), nullable=True)
    location = Column(String(200), nullable=True)
    energy = Column(String(10), default="Medium")  # High | Medium | Low
    e_class = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
