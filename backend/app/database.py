from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Idempotent column migrations. `create_all` cannot ALTER existing tables, so
# any new column added to a model must be registered here as an ALTER TABLE.
COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "courses": [
        ("credits", "INTEGER DEFAULT 3"),
    ],
    "notes": [
        ("pinned", "BOOLEAN DEFAULT 0"),
        ("updated_at", "DATETIME"),
    ],
    "courses": [
        ("google_id", "VARCHAR(100)"),
        ("curriculum_subject_id", "INTEGER"),
    ],
    "assignments": [
        ("google_id", "VARCHAR(100)"),
        ("type", "VARCHAR(30) DEFAULT 'Homework'"),
        ("type_color", "VARCHAR(20)"),
        ("time_estimate", "INTEGER"),
        ("file_url", "VARCHAR(500)"),
    ],
    "events": [
        ("google_id", "VARCHAR(100)"),
    ],
    "users": [
        ("avatar_class", "VARCHAR(50) DEFAULT 'Wizard'"),
        ("current_streak", "INTEGER DEFAULT 0"),
        ("current_weight", "FLOAT"),
        ("initial_weight", "FLOAT"),
        ("target_weight", "FLOAT"),
        ("membership_status", "VARCHAR(50) DEFAULT 'Active'"),
        ("next_payment_date", "DATE"),
        ("username", "VARCHAR(100)"),
        ("email", "VARCHAR(255)"),
        ("password_hash", "VARCHAR(255)"),
        ("role", "VARCHAR(20) DEFAULT 'student'"),
        ("is_admin", "BOOLEAN DEFAULT 0"),
        ("institution_id", "INTEGER"),
        ("program_id", "INTEGER"),
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
        # Phase 10 (Idea 98, phrase 71): goal↔subject/roadmap linkage + owner.
        ("user_id", "INTEGER"),
        ("subject_id", "INTEGER"),
        ("roadmap_id", "INTEGER"),
    ],
    "tasks": [
        ("project_id", "INTEGER"),
        ("priority_quadrant", "VARCHAR(30)"),
    ],
    "schedule_events": [
        ("event_type", "VARCHAR(50)"),
        ("location", "VARCHAR(200)"),
    ],
    # Second Brain (Phase 1): columns added after the tables first shipped.
    "kb_jobs": [
        ("ref_type", "VARCHAR(20)"),
        ("ref_id", "INTEGER"),
        ("ref_ids_json", "TEXT"),
        ("summary_json", "TEXT"),
    ],
    "kb_documents": [
        ("file_path", "VARCHAR(1000)"),
        # Phase 2 (Idea 13 metadata + Idea 20 dirty flags)
        ("author", "VARCHAR(300)"),
        ("source_url", "VARCHAR(1000)"),
        ("language", "VARCHAR(20)"),
        ("reading_time_seconds", "INTEGER"),
        ("embedding_dirty", "BOOLEAN DEFAULT 1"),
        ("graph_dirty", "BOOLEAN DEFAULT 1"),
        ("tags_dirty", "BOOLEAN DEFAULT 1"),
    ],
    "kb_sources": [
        ("duplicate_map_json", "TEXT"),
    ],
    "kb_edges": [
        # Phase 2 (Idea 16 provenance + polymorphic target)
        ("provenance", "VARCHAR(10) DEFAULT 'auto'"),
        ("target_type", "VARCHAR(20) DEFAULT 'document'"),
        ("target_concept_id", "INTEGER"),
        # Phase 9 (Idea 83) pending-edge review queue status.
        ("status", "VARCHAR(20) DEFAULT 'active'"),
    ],
    # Phase 4 (Idea 39, phrase 84): cached note-quality score + detail.
    "kb_documents": [
        ("quality_score", "INTEGER"),
        ("quality_detail", "TEXT"),
    ],
    # Phase 5 (Idea 43, phrase 21): detected term on units; (Idea 49) pacing.
    "curriculum_units": [
        ("semester", "VARCHAR(30)"),
    ],
    "users": [
        ("pacing_multiplier", "FLOAT DEFAULT 1.0"),
    ],
    # Phase 6 (Idea 51, phrase 1): study plans gained an owner.
    "study_plans": [
        ("user_id", "INTEGER"),
    ],
    # Phase 6 (Idea 58, phrase 75): mastery on topics, recomputed on writes.
    "topics": [
        ("mastery_score", "FLOAT DEFAULT 0.0"),
        ("mastery_classification", "VARCHAR(10) DEFAULT 'unknown'"),
    ],
    # Phase 9 (Automation, Ideas 81–90)
    # Idea 86: summary_dirty — set on content-hash change, consumed by the
    # nightly summary job.
    "kb_documents": [
        ("summary_dirty", "BOOLEAN DEFAULT 0"),
    ],
    # Idea 89: external-repo sync adapters.
    "kb_sources": [
        ("sync_type", "VARCHAR(20) DEFAULT 'none'"),
        ("sync_cursor_json", "TEXT"),
    ],
    # Phase 9 (Idea 85, phrase 44): auto-vs-manual flashcard candidates.
    "kb_flashcard_candidates": [
        ("source", "VARCHAR(10) DEFAULT 'manual'"),
    ],
    # Phase 6 / Idea 52 (FSRS): state columns persisted alongside the legacy
    # SM-2 display columns. Same layout as ``flashcards`` below.
    "revision_schedule": [
        ("stability", "FLOAT"),
        ("difficulty", "FLOAT"),
        ("state", "INTEGER"),
        ("step", "INTEGER"),
    ],
    # FSRS-powered flashcard review flow (Idea 52): per-card scheduler state.
    # ``fsrs_difficulty`` mirrors the model rename (the existing ``difficulty``
    # column is the display tier).
    "flashcards": [
        ("state", "INTEGER"),
        ("step", "INTEGER"),
        ("stability", "FLOAT"),
        ("fsrs_difficulty", "FLOAT"),
        ("reps", "INTEGER DEFAULT 0"),
        ("lapses", "INTEGER DEFAULT 0"),
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
        # Phase 4 (Idea 33): the legacy ``quizzes.unit_id`` column was NOT NULL.
        # SQLite cannot ALTER a column, so rebuild the table to relax it.
        _relax_quizzes_unit_id(conn)
        # Phase 2 (Ideas 15-16): ``kb_edges.target_document_id`` shipped NOT NULL,
        # but MENTIONS edges target concepts via ``target_concept_id`` (NULL
        # target document). Rebuild the table to make it nullable.
        _relax_kb_edges_target_document_id(conn)


def _relax_quizzes_unit_id(conn) -> None:
    """Rebuild ``quizzes`` with a nullable ``unit_id`` (Idea 33 note quizzes).

    Note quizzes have no curriculum unit, so the FK column must accept NULL.
    Idempotent: only rebuilds when the column is still NOT NULL. SQLite-only.
    """
    try:
        cols = conn.execute(text("PRAGMA table_info(quizzes)")).fetchall()
    except Exception:
        return  # table does not exist yet
    if not cols:
        return
    unit = next((row for row in cols if row[1] == "unit_id"), None)
    if unit is None or unit[3] == 0:  # already nullable
        return
    names = [row[1] for row in cols]
    col_defs = ", ".join(
        f'"{row[1]}" {row[2]}' + ("" if row[3] else "")  # drop NOT NULL
        + (" PRIMARY KEY" if row[5] else "")
        + (" REFERENCES curriculum_units(id)" if row[1] == "unit_id" else "")
        for row in cols
    )
    conn.execute(text(f"CREATE TABLE quizzes_new ({col_defs})"))
    conn.execute(
        text(
            f"INSERT INTO quizzes_new ({', '.join(names)}) "
            f"SELECT {', '.join(names)} FROM quizzes"
        )
    )
    conn.execute(text("DROP TABLE quizzes"))
    conn.execute(text("ALTER TABLE quizzes_new RENAME TO quizzes"))


# FK clauses the KbEdge model declares (mirrors ``Base.metadata.create_all``
# output). Re-added when the table is rebuilt because SQLite's PRAGMA
# table_info carries no FK metadata.
_KB_EDGES_FK_CLAUSES = {
    "user_id": "REFERENCES users (id)",
    "source_document_id": "REFERENCES kb_documents (id)",
    "target_document_id": "REFERENCES kb_documents (id)",
}


def _relax_kb_edges_target_document_id(conn) -> None:
    """Rebuild ``kb_edges`` with a nullable ``target_document_id``.

    Knowledge-graph edges are polymorphic: document→document edges carry a
    target document, but document→concept ``MENTIONS`` edges only carry
    ``target_concept_id`` (target document is NULL). The column shipped as
    NOT NULL in early builds, which crashed concept linking. Idempotent:
    only rebuilds while the column is still NOT NULL (or FK metadata is
    missing after an earlier rebuild). SQLite-only.
    """
    try:
        cols = conn.execute(text("PRAGMA table_info(kb_edges)")).fetchall()
    except Exception:
        return  # table does not exist yet
    if not cols:
        return
    target = next((row for row in cols if row[1] == "target_document_id"), None)
    if target is None:
        return
    fks = conn.execute(text("PRAGMA foreign_key_list(kb_edges)")).fetchall()
    if target[3] == 0 and len(fks) > 0:  # already nullable + FKs present
        return

    names = [row[1] for row in cols]

    def col_ddl(row) -> str:
        # row: cid, name, type, notnull, dflt_value, pk
        name, ctype, notnull, default, pk = row[1], row[2], row[3], row[4], row[5]
        parts = [f'"{name}" {ctype}']
        # Drop NOT NULL on the target document column only; keep it elsewhere.
        if name != "target_document_id" and notnull and not pk:
            parts.append("NOT NULL")
        if pk:
            parts.append("PRIMARY KEY")
        if default is not None:
            parts.append(f"DEFAULT {default}")
        fk = _KB_EDGES_FK_CLAUSES.get(name)
        if fk:
            parts.append(fk)
        return " ".join(parts)

    col_defs = ", ".join(col_ddl(row) for row in cols)
    conn.execute(text(f"CREATE TABLE kb_edges_new ({col_defs})"))
    conn.execute(
        text(
            f"INSERT INTO kb_edges_new ({', '.join(names)}) "
            f"SELECT {', '.join(names)} FROM kb_edges"
        )
    )
    conn.execute(text("DROP TABLE kb_edges"))
    conn.execute(text("ALTER TABLE kb_edges_new RENAME TO kb_edges"))
    # Recreate the indexes lost in the rebuild (mirrors the model's
    # ``index=True`` columns + __table_args__ index).
    conn.execute(text("CREATE INDEX ix_kb_edges_user_id ON kb_edges (user_id)"))
    conn.execute(
        text("CREATE INDEX ix_kb_edges_source_document_id ON kb_edges (source_document_id)")
    )
    conn.execute(
        text("CREATE INDEX ix_kb_edges_target_document_id ON kb_edges (target_document_id)")
    )
    conn.execute(
        text(
            "CREATE INDEX ix_kb_edges_user_docs ON kb_edges "
            "(user_id, source_document_id, target_document_id)"
        )
    )
    conn.execute(text("CREATE INDEX ix_kb_edges_relation ON kb_edges (relation)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
