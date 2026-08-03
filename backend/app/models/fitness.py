from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, ForeignKey

from app.database import Base


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    type = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    calories = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)


class FitnessGoal(Base):
    __tablename__ = "fitness_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(200), nullable=False)
    target = Column(Float, nullable=False)
    current = Column(Float, default=0.0)
    unit = Column(String(50), nullable=True)


# ── Fitness Hub models (99-phase plan, Phases 9-14) ──

class Exercise(Base):
    """A single exercise with its set/reps/weight prescription (Phase 9)."""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"))
    sets = Column(Integer, default=3)
    reps = Column(Integer, default=10)
    weight = Column(Float, default=0.0)
    user_id = Column(Integer, ForeignKey("users.id"))


class MuscleGroup(Base):
    """Anatomical muscle group with Upper/Lower body-part tag (Phase 10)."""
    __tablename__ = "muscle_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    body_part = Column(String(20), default="Upper")  # Upper / Lower
    image_3d_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))


class WorkoutSplit(Base):
    """A day's PUSH/PULL/LEG split with its exercise list (Phase 11)."""
    __tablename__ = "workout_splits"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, default=0)  # 0=Mon ... 6=Sun
    split_name = Column(String(20), default="PUSH")  # PUSH / PULL / LEG / REST
    exercise_list = Column(Text, nullable=True)  # JSON array of exercise names
    week_number = Column(Integer, default=1)
    user_id = Column(Integer, ForeignKey("users.id"))


class Expense(Base):
    """Fitness expense (Phase 12)."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    cost = Column(Float, default=0.0)
    date = Column(Date, nullable=False)
    category = Column(String(50), default="Supplement")  # Supplement / Equipment / Gym
    user_id = Column(Integer, ForeignKey("users.id"))


class PersonalRecord(Base):
    """Lift PR: current vs target weight (Phase 13)."""
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, index=True)
    exercise_name = Column(String(200), nullable=False)
    current_weight = Column(Float, default=0.0)
    target_weight = Column(Float, default=0.0)
    unit = Column(String(20), default="kg")
    user_id = Column(Integer, ForeignKey("users.id"))


class DietPlan(Base):
    """Diet phase: Diet / Bulking / Cutting / Maintenance (Phase 14)."""
    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))
