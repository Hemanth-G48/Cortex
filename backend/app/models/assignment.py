from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    due_date = Column(Date, nullable=False)
    status = Column(String(50), default="Not started")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    date = Column(Date, nullable=False)
    status = Column(String(50), default="Not started")
