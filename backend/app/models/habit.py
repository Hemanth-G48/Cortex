from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey

from app.database import Base


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(20), default="daily")  # daily / weekly
    target_count = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    color_theme = Column(String(20), default="blue")  # blue / green / orange / red
    is_archived = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Audit defect #49: why the habit was archived + (optionally) the vault
    # document that triggered an automatic archive, so the Archive page can
    # explain the state instead of showing a bare "Archived" chip.
    archived_reason = Column(String(300), nullable=True)
    archived_document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=True)

    # Gamified Habit Tracker fields (99-phase plan, Phases 1-3)
    habit_type = Column(String(20), default="good")  # good / bad
    xp_reward = Column(Integer, default=30)
    xp_penalty = Column(Integer, default=20)
    image_url = Column(String(500), nullable=True)
    days_caught = Column(Integer, default=0)

    # Fitness Hub (Phase 3): goal text + cached 7x7 heatmap JSON
    goal = Column(String(300), nullable=True)
    heatmap_data = Column(Text, nullable=True)


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id"))
    date = Column(Date, nullable=False)
    completed = Column(Boolean, default=False)
    count = Column(Integer, default=1)

    # Gamified Habit Tracker fields (Phase 4): Good/Bad, Completed/Shit, ±XP
    type = Column(String(10), default="good")  # good / bad
    status = Column(String(20), default="Completed")  # Completed / Shit I did it
    xp_change = Column(Integer, default=0)
    # Phase 91: drag-and-drop sort within a calendar day column
    sort_order = Column(Integer, default=0)
