from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Idempotent column migrations. `create_all` cannot ALTER existing tables, so
# any new column added to a model must be registered here as an ALTER TABLE.
COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("avatar_class", "VARCHAR(50) DEFAULT 'Wizard'"),
        ("current_streak", "INTEGER DEFAULT 0"),
        ("current_weight", "FLOAT"),
        ("initial_weight", "FLOAT"),
        ("target_weight", "FLOAT"),
        ("membership_status", "VARCHAR(50) DEFAULT 'Active'"),
        ("next_payment_date", "DATE"),
    ],
    "missions": [
        ("linked_quests", "VARCHAR(500)"),
    ],
    "life_areas": [
        ("target_days", "INTEGER"),
        ("status", "VARCHAR(50) DEFAULT 'In progress'"),
        ("total_xp_earned", "INTEGER DEFAULT 0"),
    ],
    "habits": [
        ("color_theme", "VARCHAR(20) DEFAULT 'blue'"),
        ("is_archived", "BOOLEAN DEFAULT 0"),
        ("habit_type", "VARCHAR(20) DEFAULT 'good'"),
        ("xp_reward", "INTEGER DEFAULT 30"),
        ("xp_penalty", "INTEGER DEFAULT 20"),
        ("image_url", "VARCHAR(500)"),
        ("days_caught", "INTEGER DEFAULT 0"),
        ("goal", "VARCHAR(300)"),
        ("heatmap_data", "TEXT"),
    ],
    "habit_logs": [
        ("type", "VARCHAR(10) DEFAULT 'good'"),
        ("status", "VARCHAR(20) DEFAULT 'Completed'"),
        ("xp_change", "INTEGER DEFAULT 0"),
        ("sort_order", "INTEGER DEFAULT 0"),
    ],
    "pomodoro_sessions": [
        ("mode", "VARCHAR(10) DEFAULT 'Focus'"),
    ],
    "goals": [
        ("habit_id", "INTEGER"),
        ("target_date", "DATE"),
        ("is_completed", "BOOLEAN DEFAULT 0"),
    ],
    "tasks": [
        ("project_id", "INTEGER"),
        ("priority_quadrant", "VARCHAR(30)"),
    ],
    "schedule_events": [
        ("event_type", "VARCHAR(50)"),
        ("location", "VARCHAR(200)"),
    ],
}


def migrate_schema() -> None:
    """Add missing columns to existing tables (safe to run every startup)."""
    with engine.begin() as conn:
        for table, cols in COLUMN_MIGRATIONS.items():
            try:
                # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
                existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            except Exception:
                continue  # table does not exist yet
            for col, ddl in cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
