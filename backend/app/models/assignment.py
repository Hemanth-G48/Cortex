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
    google_id = Column(String(100), nullable=True)
    # STUDENT-PLANAR G6 (Phase 37): type taxonomy + attachment support.
    type = Column(String(30), default="Homework")  # Homework | Quiz | Project | Test | Other
    type_color = Column(String(20), nullable=True)
    time_estimate = Column(Integer, nullable=True)  # minutes
    file_url = Column(String(500), nullable=True)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))
    date = Column(Date, nullable=False)
    status = Column(String(50), default="Not started")
