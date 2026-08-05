"""STUDENT-PLANAR demo seed data (idempotent / append-only).

Adds the demo dataset that makes the ported STUDENT-PLANAR features (reading
tracker, brain dump, daily schedule, teacher role, assignment taxonomy)
verifiable out of the box:

- A demo student (the existing first user) gets ``username``/``email``/``password``
  so credential login works.
- A demo teacher is created so the teacher dashboard has data.
- A small reading shelf (3 books across categories).
- Assignment ``type`` backfilled to ``Homework`` on legacy rows.
- A demo daily-schedule day with one block per category.

Every function is safe to call on every startup and never duplicates rows.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Assignment, Book, BrainDump, DailyScheduleItem, User
from app.services.security import hash_password

DEMO_TEACHER_USERNAME = "demo.teacher"
DEMO_TEACHER_EMAIL = "teacher@student-os.dev"
DEMO_PASSWORD = "demo-password-123"


def seed_student_planar(db: Session) -> None:
    """Run all STUDENT-PLANAR demo seeds (each idempotent)."""
    seed_demo_student_teacher(db)
    seed_demo_books(db)
    seed_assignment_types(db)
    seed_daily_schedule_demo(db)
    seed_demo_braindump(db)
    db.commit()


def seed_demo_student_teacher(db: Session) -> None:
    """Give the first user credentials (demo student) and create a demo teacher."""
    user = db.query(User).first()
    if user is None:
        return

    # Demo student: fill in login credentials only when empty so we never
    # overwrite a username/email the user has set up themselves.
    if not user.username:
        user.username = "alex"
    if not user.email:
        user.email = "alex@student-os.dev"
    if not user.password_hash:
        user.password_hash = hash_password(DEMO_PASSWORD)
    if not user.role:
        user.role = "student"

    # Demo teacher: created once, keyed on username.
    existing = db.query(User).filter(
        (User.username == DEMO_TEACHER_USERNAME) | (User.email == DEMO_TEACHER_EMAIL)
    ).first()
    if existing:
        return
    db.add(User(
        name="Demo Teacher",
        username=DEMO_TEACHER_USERNAME,
        email=DEMO_TEACHER_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        role="teacher",
        avatar_class="Wizard",
        current_level=1,
        total_xp=0,
    ))


def seed_demo_books(db: Session) -> None:
    """Demo reading shelf: one finished / reading / want book for the first user."""
    user = db.query(User).first()
    if user is None:
        return

    spec = [
        ("Clean Code", "Robert C. Martin", "finished"),
        ("The Pragmatic Programmer", "Andrew Hunt", "reading"),
        ("Deep Work", "Cal Newport", "want"),
    ]
    existing = {(b.title, b.user_id) for b in db.query(Book).all()}
    for title, author, category in spec:
        if (title, user.id) in existing:
            continue
        db.add(Book(
            user_id=user.id,
            title=title,
            author=author,
            category=category,
        ))


def seed_assignment_types(db: Session) -> None:
    """Backfill ``type`` on legacy assignment rows (default Homework)."""
    for row in db.query(Assignment).filter(
        (Assignment.type.is_(None)) | (Assignment.type == "")
    ).all():
        row.type = "Homework"


def seed_daily_schedule_demo(db: Session) -> None:
    """Demo day: one block per category (School / Study Time / Break) for today."""
    user = db.query(User).first()
    if user is None:
        return

    today = date.today()
    spec = [
        ("08:00-09:30", "Data Structures Lecture", "School", "High", "Room 204"),
        ("10:00-11:30", "Deep Work: Algorithms HW", "Study Time", "High", "Library"),
        ("13:00-14:00", "Lunch & Recharge", "Break", "Low", "Cafeteria"),
    ]
    existing = {(s.user_id, s.date, s.time_range) for s in db.query(DailyScheduleItem).all()}
    for time_range, activity, category, energy, location in spec:
        if (user.id, today, time_range) in existing:
            continue
        db.add(DailyScheduleItem(
            user_id=user.id,
            date=today,
            time_range=time_range,
            activity=activity,
            category=category,
            cat_class=f"cat-{category.lower().replace(' ', '-')}",
            location=location,
            energy=energy,
            e_class=f"e-{energy.lower()}",
        ))


def seed_demo_braindump(db: Session) -> None:
    """Seed a starter brain dump only when the user has no row yet."""
    user = db.query(User).first()
    if user is None:
        return
    if db.query(BrainDump).filter(BrainDump.user_id == user.id).first():
        return
    db.add(BrainDump(
        user_id=user.id,
        content="Quick-capture your thoughts here — they auto-save.",
        updated_at=datetime.now(),
    ))
