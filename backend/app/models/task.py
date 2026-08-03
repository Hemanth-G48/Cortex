from sqlalchemy import Column, Integer, String, Date, Time, Boolean, ForeignKey
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject_tag = Column(String(50), nullable=True)
    priority_tag = Column(String(10), nullable=True)  # High/Medium/Low
    priority_quadrant = Column(String(30), nullable=True)  # Urgent/Important | Important/Not Urgent | Urgent/Not Important | Not Important/Not Urgent
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="Not started")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    time = Column(Time, nullable=True)
    date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False)


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(String(10), nullable=False)  # Mon–Fri
    time_slot = Column(String(50), nullable=False)
    subject_name = Column(String(100), nullable=False)
    color = Column(String(20), nullable=True)
