from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from app.database import Base


class Grade(Base):
    """A single graded item (assignment/exam) within a course."""

    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    assignment_id = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False, default="Assignment")
    points_earned = Column(Float, default=0.0)
    points_possible = Column(Float, default=0.0)
    category_id = Column(Integer, ForeignKey("course_weights.id"), nullable=True)
    date = Column(Date, nullable=True)


class CourseWeight(Base):
    """Weighted grading category for a course (e.g. Homework 25%, Midterm 25%)."""

    __tablename__ = "course_weights"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    weight = Column(Float, default=0.0)
