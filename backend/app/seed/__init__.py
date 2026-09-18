from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.seed.curriculum import seed_curriculum
from app.seed.materials_seed import parts_demo_materials

from app.models import (
    Assignment,
    Character,
    Course,
    CourseWeight,
    Flashcard,
    FlashcardDeck,
    Grade,
    StudyPlan,
    DailyLog,
    DietPlan,
    Event,
    Exam,
    Exercise,
    Expense,
    FitnessGoal,
    Goal,
    Habit,
    HabitLog,
    JournalEntry,
    LifeArea,
    Mission,
    MissionTask,
    MoodLog,
    MuscleGroup,
    Note,
    PersonalRecord,
    PomodoroSession,
    Project,
    ProjectTask,
    Quest,
    QuestTask,
    Reminder,
    Reward,
    Schedule,
    ScheduleEvent,
    SleepLog,
    Task,
    User,
    Workout,
    WorkoutSplit,
)
def seed_database(db: Session) -> None:
    user = db.query(User).first()
    fresh = user is None
    if not user:
        seed_full(db)
    # SyllabusAI curriculum catalog (idempotent): Institution → Program →
    # Subject → Unit. Called unconditionally so demo catalog is always present.
    seed_curriculum(db)
    # SyllabusAI materials: idempotent, safe if no curriculum units exist yet.
    parts_demo_materials(db)
    # SyllabusAI (G1): the single local user is the admin/curator so admin-gated
    # catalog endpoints are usable out of the box (backfill for existing DBs).
    if user and db.query(User).count() == 1 and not user.is_admin:
        user.is_admin = True
        db.commit()
    seed_rpg_additions(db)
    # Vault demo data seeded only on first boot (like other demo data) so user
    # deletions are never resurrected on restart.
    if fresh:
        seed_vault_habits(db)
        seed_vault_demo(db)
    # Life Planner demo data (daily logs + events) is append-only: entries are
    # keyed on (date / title) so re-runs never duplicate them.
    seed_life_planner_demo(db)
    # Gamified Habit Tracker data (Phases 25-31): append-only + idempotent.
    seed_habit_tracker(db)
    # Fitness Hub data (Phases 41-42): idempotent.
    seed_fitness_hub(db)
    # Grades/GPA demo data (99-phase plan, Phases 15): idempotent.
    seed_grades(db)
    # Flashcard demo decks (99-phase plan, Phase 30): idempotent.
    seed_flashcards(db)
    # Study plan demo (99-phase plan, Phase 43): idempotent.
    seed_study_plans(db)
    # Mood tracking demo (Zenith-Study-Planner G2): idempotent on logged_at.
    seed_mood(db)
    # Sleep tracker demo (Zenith-Study-Planner G3): idempotent on date.
    seed_sleep(db)


def seed_full(db: Session) -> None:
    # -- User --
    user = User(name="Alex", current_level=5, total_xp=2340, avatar_class="Wizard", current_streak=3, is_admin=True)
    db.add(user)
    db.flush()

    # -- RPG Character --
    seed_character(db, user)

    # -- Courses --
    courses_data = [
        ("Computer Science", 2, 4, 3, 4, "In progress"),
        ("OOP", 3, 5, 2, 3, "In progress"),
        ("Algorithms", 1, 3, 2, 3, "In progress"),
        ("Software", 4, 5, 1, 3, "In progress"),
        ("Data Structures", 0, 3, 0, 3, "Not started"),
    ]
    courses = []
    for title, cur_as, tot_as, cur_ex, tot_ex, status in courses_data:
        c = Course(
            title=title,
            current_assignment=cur_as,
            total_assignments=tot_as,
            next_exam=cur_ex,
            total_exams=tot_ex,
            status=status,
            user_id=user.id,
        )
        db.add(c)
        courses.append(c)
    db.flush()

    # -- Assignments (2–4 per course) --
    assignments_data = [
        (courses[0], "Linked Lists Review", date(2026, 3, 15), "Completed"),
        (courses[0], "Sorting Algorithms", date(2026, 4, 10), "Completed"),
        (courses[0], "Graph Theory Basics", date(2026, 5, 5), "In progress"),
        (courses[1], "Inheritance Diagrams", date(2026, 3, 20), "Completed"),
        (courses[1], "Polymorphism Essay", date(2026, 4, 15), "Completed"),
        (courses[1], "Design Patterns", date(2026, 5, 10), "Not started"),
        (courses[2], "Big O Notation", date(2026, 4, 1), "Completed"),
        (courses[2], "Recursion Problems", date(2026, 5, 1), "In progress"),
        (courses[3], "Requirements Doc", date(2026, 3, 25), "Completed"),
        (courses[3], "Sprint Planning", date(2026, 4, 20), "Completed"),
        (courses[3], "Code Review Setup", date(2026, 5, 15), "Not started"),
        (courses[4], "Array vs Linked List", date(2026, 4, 5), "Not started"),
    ]
    for course, title, due, status in assignments_data:
        db.add(Assignment(title=title, course_id=course.id, due_date=due, status=status))

    # -- Exams (1 per course) --
    exams_data = [
        (courses[0], "CS Midterm", date(2026, 4, 20)),
        (courses[1], "OOP Final", date(2026, 5, 10)),
        (courses[2], "Algorithms Test", date(2026, 5, 5)),
        (courses[3], "Software Exam", date(2026, 4, 25)),
        (courses[4], "Data Structures Quiz", date(2026, 5, 15)),
    ]
    for course, title, exam_date in exams_data:
        db.add(Exam(title=title, course_id=course.id, date=exam_date, status="Not started"))

    # -- Goals --
    goals_data = [
        ("Freshman Foundation", "Q1", 47.0, 2026),
        ("Mid-Year Momentum", "Q2", 68.0, 2026),
        ("Senior Prep", "Q3", 12.0, 2026),
        ("Final Stretch", "Q4", 0.0, 2026),
    ]
    for title, qtr, prog, yr in goals_data:
        db.add(Goal(title=title, quarter=qtr, progress_percentage=prog, year=yr))

    # -- Tasks --
    tasks_data = [
        ("Complete Algorithms homework", "Algorithms", "High", date(2026, 5, 20), "Not started", user.id),
        ("Review OOP notes", "OOP", "Medium", date(2026, 5, 18), "In progress", user.id),
        ("Prepare CS presentation", "Computer Science", "High", date(2026, 5, 22), "Not started", user.id),
        ("Read Software chapter 5", "Software", "Medium", date(2026, 5, 19), "Not started", user.id),
        ("Practice Data Structures", "Data Structures", "Low", date(2026, 5, 25), "Not started", user.id),
        ("Submit OOP assignment", "OOP", "High", date(2026, 5, 17), "Not started", user.id),
        ("Group study session", "Computer Science", "Medium", date(2026, 5, 21), "Not started", user.id),
        ("Review Algorithms quiz", "Algorithms", "Low", date(2026, 5, 23), "Completed", user.id),
    ]
    quadrant_by_priority = {"High": "Urgent/Important", "Medium": "Important/Not Urgent", "Low": "Not Important/Not Urgent"}
    for title, subj, pri, due, status, uid in tasks_data:
        db.add(Task(
            title=title, subject_tag=subj, priority_tag=pri,
            priority_quadrant=quadrant_by_priority[pri],
            due_date=due, status=status, user_id=uid,
        ))

    # -- Reminders --
    reminders_data = [
        ("Team meeting at 09:00", date(2026, 5, 20), time(9, 0)),
        ("Night out with friends", date(2026, 5, 22), time(18, 30)),
        ("Study group", date(2026, 5, 21), time(14, 0)),
    ]
    for title, rdate, rtime in reminders_data:
        db.add(Reminder(title=title, date=rdate, time=rtime))

    # -- Schedule (Mon–Fri) --
    schedule_data = [
        ("Mon", "8:00-10:00", "Computer Science", "#e8496d"),
        ("Mon", "10:00-11:00", "OOP", "#4ecdc4"),
        ("Mon", "11:00-12:00", "Study Hall", "#95e1d3"),
        ("Tue", "8:00-10:00", "Algorithms", "#f9ca24"),
        ("Tue", "10:00-12:00", "Software", "#6c5ce7"),
        ("Wed", "8:00-10:00", "Computer Science", "#e8496d"),
        ("Wed", "10:00-11:00", "Data Structures", "#00b894"),
        ("Wed", "11:00-12:00", "OOP", "#4ecdc4"),
        ("Thu", "8:00-10:00", "Algorithms", "#f9ca24"),
        ("Thu", "10:00-11:00", "Software", "#6c5ce7"),
        ("Fri", "8:00-10:00", "Data Structures", "#00b894"),
        ("Fri", "10:00-11:00", "Computer Science", "#e8496d"),
        ("Fri", "11:00-12:00", "Study Hall", "#95e1d3"),
    ]
    for day, slot, subj, color in schedule_data:
        db.add(Schedule(day=day, time_slot=slot, subject_name=subj, color=color))

    # -- Notes (1 per course) --
    notes_data = [
        ("CS Chapter 1 Summary", "Key concepts from chapter 1 covering data structures and algorithms basics.", courses[0].id, date(2026, 3, 10)),
        ("OOP Pillars", "Encapsulation, Inheritance, Polymorphism, and Abstraction — the four pillars.", courses[1].id, date(2026, 3, 12)),
        ("Algorithm Complexities", "Big O: O(1), O(log n), O(n), O(n log n), O(n²) cheat sheet.", courses[2].id, date(2026, 3, 15)),
        ("SDLC Overview", "Requirements → Design → Implementation → Testing → Deployment → Maintenance.", courses[3].id, date(2026, 3, 18)),
        ("DS Types", "Arrays, Linked Lists, Stacks, Queues, Trees, Graphs — comparisons.", courses[4].id, date(2026, 3, 20)),
    ]
    for title, content, cid, cdate in notes_data:
        db.add(Note(title=title, content=content, course_id=cid, created_date=cdate))

    # -- Habits --
    db.add(Habit(name="Morning Exercise", description="30 min workout", frequency="daily", target_count=1, current_streak=3, longest_streak=7, user_id=user.id))
    db.add(Habit(name="Read 20 pages", description="Daily reading habit", frequency="daily", target_count=1, current_streak=5, longest_streak=14, user_id=user.id))
    db.add(Habit(name="Review Notes", description="Review weekly notes", frequency="weekly", target_count=1, current_streak=2, longest_streak=6, user_id=user.id))

    # -- Habit Logs --
    from datetime import timedelta
    today = date.today()
    for i in range(5):
        db.add(HabitLog(habit_id=1, date=today - timedelta(days=i), completed=True))
        db.add(HabitLog(habit_id=2, date=today - timedelta(days=i), completed=True))

    # -- Pomodoro Sessions --
    db.add(PomodoroSession(user_id=user.id, start_time=datetime.now(), duration_minutes=25, completed=True, task_description="Algorithms homework"))
    db.add(PomodoroSession(user_id=user.id, start_time=datetime.now(), duration_minutes=25, completed=True, task_description="OOP review"))
    db.add(PomodoroSession(user_id=user.id, start_time=datetime.now(), duration_minutes=25, completed=False, task_description="CS project"))

    # -- Workouts --
    db.add(Workout(user_id=user.id, date=today, type="Running", duration_minutes=30, calories=250))
    db.add(Workout(user_id=user.id, date=today - timedelta(days=1), type="Cycling", duration_minutes=45, calories=350))
    db.add(Workout(user_id=user.id, date=today - timedelta(days=2), type="Yoga", duration_minutes=20, calories=80))

    # -- Fitness Goals --
    db.add(FitnessGoal(user_id=user.id, name="Run 100km", target=100.0, current=45.0, unit="km"))
    db.add(FitnessGoal(user_id=user.id, name="Workout Days", target=30.0, current=12.0, unit="days"))

    # -- Journal Entries --
    db.add(JournalEntry(user_id=user.id, date=today - timedelta(days=2), content="Had a productive study session. Feeling confident about the upcoming exams.", mood="happy", tags="study,productive"))
    db.add(JournalEntry(user_id=user.id, date=today - timedelta(days=1), content="Need to focus more on Data Structures. The material is getting harder.", mood="neutral", tags="struggle,dsa"))

    # -- Quests --
    quest1 = Quest(user_id=user.id, title="Master Algorithms", description="Complete all algorithms assignments with A grade", xp_reward=200, status="In progress", due_date=today + timedelta(days=14))
    db.add(quest1)
    quest2 = Quest(user_id=user.id, title="Fitness Challenge", description="Work out 5 days a week for a month", xp_reward=150, status="In progress")
    db.add(quest2)
    db.flush()
    db.add(QuestTask(quest_id=quest1.id, title="Complete sorting algorithms"))
    db.add(QuestTask(quest_id=quest1.id, title="Practice dynamic programming"))
    db.add(QuestTask(quest_id=quest1.id, title="Pass the final quiz"))

    # -- Projects --
    proj1 = Project(user_id=user.id, name="Study Portal", description="Build a web app for course management", status="In progress", deadline=today + timedelta(days=30))
    db.add(proj1)
    db.flush()
    db.add(ProjectTask(project_id=proj1.id, title="Design database schema"))
    db.add(ProjectTask(project_id=proj1.id, title="Implement user auth"))

    # -- Life Areas --
    # LifeArea seeding is owned by seed_rpg_additions (the richer canonical
    # set: progress/target_days/status) so fresh boots get exactly one set.

    # -- Rewards --
    seed_rewards(db, user)
    # -- Missions --
    seed_missions(db, user)
    # -- Schedule Events --
    seed_schedule_events(db, user)

    db.commit()


def seed_study_plans(db: Session) -> None:
    """Study plan demo (99-phase plan, Phase 43). Idempotent on subject."""
    import json as _json

    if db.query(StudyPlan).first():
        return
    weeks = [
        {"week": 1, "topic": "Cell Biology & Organelles", "tasks": ["Read Ch 1-2", "Make flashcards", "Practice diagrams"]},
        {"week": 2, "topic": "Genetics & DNA", "tasks": ["Read Ch 3-4", "Punnett square practice", "Review lecture notes"]},
        {"week": 3, "topic": "Evolution & Ecology", "tasks": ["Read Ch 5-6", "Watch videos", "Past exam questions"]},
        {"week": 4, "topic": "Review & Practice Exams", "tasks": ["Full practice test", "Review weak areas", "Final revision"]},
    ]
    db.add(StudyPlan(
        subject="Biology Final",
        exam_date=None,
        weeks_json=_json.dumps(weeks, ensure_ascii=False),
    ))
    db.commit()


def seed_flashcards(db: Session) -> None:
    """Flashcard demo decks (99-phase plan, Phase 30).

    Idempotent / append-only: decks keyed on name, cards on (deck, front).
    Two decks with 5-6 cards each, mirroring Shiori's DEMO_DECKS.
    """
    courses = db.query(Course).order_by(Course.id).all()
    deck_spec = [
        (
            "Integration Techniques",
            courses[0].id if courses else None,
            [
                ("What is the formula for Integration by Parts?", "∫u dv = uv − ∫v du. Remember LIATE for choosing u.", "basic", 3),
                ("When do you use u-substitution?", "When the integrand contains a composite function f(g(x))·g'(x). Let u = g(x), du = g'(x)dx.", "easy", 2),
                ("What substitution is used for √(a²−x²)?", "x = a·sin(θ). This converts the square root to a·cos(θ).", "medium", 0),
                ("What does LIATE stand for?", "Logarithms → Inverse trig → Algebraic → Trig → Exponential. Choose u as whichever comes first.", "basic", 1),
                ("∫ sin²(x) dx = ?", "Use the half-angle identity: sin²(x) = (1 − cos(2x))/2 → x/2 − sin(2x)/4 + C.", "hard", 0),
            ],
        ),
        (
            "Data Structures — Key Concepts",
            courses[1].id if len(courses) > 1 else None,
            [
                ("Time complexity of BST search (average case)?", "O(log n) average, O(n) worst case (degenerate tree).", "easy", 2),
                ("What traversal gives a BST in sorted order?", "Inorder traversal (Left → Root → Right) always produces ascending sorted output.", "basic", 3),
                ("Difference between BFS and DFS?", "BFS uses a queue (level by level, shortest path); DFS uses a stack/recursion (depth-first, cycle detection).", "medium", 1),
                ("What is amortized O(1) for dynamic arrays?", "Appends are O(1) amortized because doubling the array rarely occurs; n operations cost O(n) total.", "hard", 0),
            ],
        ),
    ]

    existing_decks = {d.name: d for d in db.query(FlashcardDeck).all()}
    for name, cid, cards in deck_spec:
        deck = existing_decks.get(name)
        if not deck:
            deck = FlashcardDeck(name=name, course_id=cid)
            db.add(deck)
            db.flush()
            existing_decks[name] = deck
        have = {c.front for c in deck.cards}
        for front, back, difficulty, streak in cards:
            if front in have:
                continue
            db.add(Flashcard(
                deck_id=deck.id, front=front, back=back,
                difficulty=difficulty, streak=streak,
            ))

    db.commit()


def seed_grades(db: Session) -> None:
    """Grades/GPA demo data (99-phase plan, Phase 15).

    Idempotent / append-only: weights keyed on (course_id, name) and grades on
    (course_id, title). Seeded for the first two demo courses so the Grades
    page + cumulative GPA have data out of the box.
    """
    courses = db.query(Course).order_by(Course.id).all()
    if len(courses) < 2:
        return

    # ── Weighted categories for course 1 (Computer Science) ──
    weight_spec = [("Homework", 25.0), ("Quizzes", 25.0), ("Midterm", 25.0), ("Final Exam", 25.0)]
    existing_weights = {(w.course_id, w.name) for w in db.query(CourseWeight).all()}
    weight_ids: dict[str, int] = {}
    for name, weight in weight_spec:
        key = (courses[0].id, name)
        if key not in existing_weights:
            w = CourseWeight(course_id=courses[0].id, name=name, weight=weight)
            db.add(w)
            db.flush()
            weight_ids[name] = w.id
            existing_weights.add(key)
        else:
            weight_ids[name] = db.query(CourseWeight).filter(
                CourseWeight.course_id == courses[0].id, CourseWeight.name == name
            ).first().id

    # ── Grade entries for course 1 (categorized) + course 2 (plain) ──
    grade_spec = [
        (courses[0].id, "HW 1 — Linked Lists", 48.0, 50.0, weight_ids.get("Homework")),
        (courses[0].id, "HW 2 — Sorting", 44.0, 50.0, weight_ids.get("Homework")),
        (courses[0].id, "Quiz 1", 18.0, 20.0, weight_ids.get("Quizzes")),
        (courses[0].id, "Midterm 1", 138.0, 150.0, weight_ids.get("Midterm")),
        (courses[1].id, "Array vs Linked List", 95.0, 100.0, None),
        (courses[1].id, "Stacks & Queues", 88.0, 100.0, None),
    ]
    existing_grades = {(g.course_id, g.title) for g in db.query(Grade).all()}
    for cid, title, earned, possible, cat_id in grade_spec:
        if (cid, title) in existing_grades:
            continue
        db.add(Grade(
            course_id=cid, title=title,
            points_earned=earned, points_possible=possible,
            category_id=cat_id,
        ))

    db.commit()


def seed_life_planner_demo(db: Session) -> None:
    """Append-only Life Planner demo data: 7 daily logs and a few one-off events
    with locations. Entries are keyed on date/title so re-seeding never duplicates."""
    user = db.query(User).first()
    if not user:
        return

    today = date.today()
    existing_log_dates = {l.date for l in db.query(DailyLog).all()}
    focused_minutes = [45, 60, 30, 90, 45, 0, 120]
    for i, minutes in enumerate(focused_minutes):
        log_date = today - timedelta(days=i)
        if log_date in existing_log_dates:
            continue
        db.add(DailyLog(
            user_id=user.id,
            date=log_date,
            time_focused=minutes,
            status="active" if minutes > 0 else "inactive",
        ))

    existing_event_titles = {e.title for e in db.query(Event).all()}
    events = [
        ("Lunch with Sarah", today, time(13, 0), "Bistro 21"),
        ("Dentist appointment", today + timedelta(days=1), time(10, 0), "Sunrise Dental"),
        ("Team meeting", today + timedelta(days=2), time(16, 30), "Conf Room B"),
        ("Grocery run", today + timedelta(days=3), time(18, 0), "Fresh Market"),
        ("Movie night", today + timedelta(days=4), time(19, 30), "Cinema City"),
    ]
    for title, edate, etime, location in events:
        if title in existing_event_titles:
            continue
        db.add(Event(
            user_id=user.id,
            title=title,
            date=edate,
            time=etime,
            location=location,
            is_completed=False,
        ))
    db.commit()


def seed_habit_tracker(db: Session) -> None:
    """Gamified Habit Tracker seed data (99-phase plan, Phases 25-31).

    Idempotent / append-only: habits are keyed on name, logs on
    (habit, date), rewards on title, pomodoro sessions on task description
    and life-area XP totals are only filled when empty.
    """
    user = db.query(User).first()
    if not user:
        return

    # ── Phase 25/26: good + bad habits ──
    good_spec = [
        ("Deep Work", "Focused, distraction-free work blocks", 30),
        ("Workout", "Daily exercise session", 30),
        ("Healthy Diet", "Eat balanced, nutritious meals", 30),
        ("Reading", "Daily reading habit", 30),
        ("Good Sleep", "7-8 hours of quality sleep", 30),
    ]
    bad_spec = [
        ("Smoking", "Caught smoking — that's a penalty!", 20),
        ("Alcohol", "Drank alcohol", 20),
        ("Fast Food", "Ate fast food", 20),
        ("High Screen Time", "Excessive screen time", 20),
        ("Bad Sleep", "Stayed up too late / poor sleep", 20),
    ]

    existing = {h.name: h for h in db.query(Habit).all()}
    good_objs: list[Habit] = []
    bad_objs: list[Habit] = []
    for name, desc, xp in good_spec:
        h = existing.get(name)
        if h:
            if h.habit_type != "good":
                h.habit_type = "good"
            if h.xp_reward != xp:
                h.xp_reward = xp
            good_objs.append(h)
            continue
        h = Habit(
            name=name, description=desc, frequency="daily", target_count=1,
            habit_type="good", xp_reward=xp, xp_penalty=20,
            current_streak=2, longest_streak=4, user_id=user.id,
        )
        db.add(h)
        good_objs.append(h)
    for name, desc, penalty in bad_spec:
        h = existing.get(name)
        if h:
            if h.habit_type != "bad":
                h.habit_type = "bad"
            if h.xp_penalty != penalty:
                h.xp_penalty = penalty
            bad_objs.append(h)
            continue
        h = Habit(
            name=name, description=desc, frequency="daily", target_count=1,
            habit_type="bad", xp_reward=30, xp_penalty=penalty,
            current_streak=0, days_caught=2, user_id=user.id,
        )
        db.add(h)
        bad_objs.append(h)
    db.flush()

    # ── Phase 27: logs for the past 7 days (Completed / Shit I did it) ──
    today = date.today()
    for h in good_objs:
        have = {str(l.date) for l in db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()}
        for i in range(7):
            day = today - timedelta(days=i)
            if str(day) in have:
                continue
            if (i + h.id) % 3 == 0:
                continue
            db.add(HabitLog(
                habit_id=h.id, date=day, completed=True, count=1,
                type="good", status="Completed", xp_change=h.xp_reward,
            ))
    for h in bad_objs:
        have = {str(l.date) for l in db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()}
        for i in range(7):
            day = today - timedelta(days=i)
            if str(day) in have:
                continue
            if (i + h.id) % 4 == 0:
                continue
            db.add(HabitLog(
                habit_id=h.id, date=day, completed=True, count=1,
                type="bad", status="Shit I did it", xp_change=-h.xp_penalty,
            ))

    # Backfill unset xp_change on completed logs so calendars read ±XP.
    # (completed=False rows are left untouched — they carry no XP change.)
    for h in good_objs:
        if (h.xp_reward or 0) > 0:
            for log in db.query(HabitLog).filter(
                HabitLog.habit_id == h.id,
                HabitLog.xp_change == 0,
                HabitLog.completed == True,  # noqa: E712
            ).all():
                log.xp_change = h.xp_reward
                log.type = "good"
                log.status = "Completed"
    for h in bad_objs:
        if (h.xp_penalty or 0) > 0:
            for log in db.query(HabitLog).filter(
                HabitLog.habit_id == h.id,
                HabitLog.xp_change == 0,
                HabitLog.completed == True,  # noqa: E712
            ).all():
                log.xp_change = -h.xp_penalty
                log.type = "bad"
                log.status = "Shit I did it"

    # ── Phase 28: the 4 spec rewards (one pre-claimed for the Claimed tab) ──
    spec_rewards = [
        ("Go for a walk", "Take a relaxing walk outside", 30, "Lifestyle", False),
        ("Watch movie", "Movie night at home", 50, "Entertainment", True),
        ("Eat outside", "Treat yourself to a meal out", 60, "Food", False),
        ("Day off", "A full guilt-free rest day", 80, "Lifestyle", False),
    ]
    existing_rewards = {r.title for r in db.query(Reward).all()}
    for title, desc, cost, cat, claimed in spec_rewards:
        if title in existing_rewards:
            continue
        db.add(Reward(
            user_id=user.id, title=title, description=desc, xp_cost=cost,
            category=cat, is_available=not claimed,
            claimed_date=datetime.now() - timedelta(days=1) if claimed else None,
        ))

    # ── Phase 29: pomodoro sessions with mode ──
    existing_pomo = {s.task_description for s in db.query(PomodoroSession).all()}
    pomo_spec = [
        ("Deep work session", 25, True, "Focus"),
        ("Study block", 50, True, "Focus"),
        ("Short recharge", 5, True, "Break"),
        ("Late night focus", 25, False, "Focus"),
    ]
    for task_desc, minutes, completed, mode in pomo_spec:
        if task_desc in existing_pomo:
            continue
        db.add(PomodoroSession(
            user_id=user.id, start_time=datetime.now(), duration_minutes=minutes,
            completed=completed, task_description=task_desc, mode=mode,
        ))

    # ── Phase 30: life-area "All Time XP" totals ──
    area_xp = {"Health": 58, "Fitness": 34, "Self Development": 42, "Work": 27}
    for area in db.query(LifeArea).all():
        if area.total_xp_earned:
            continue
        area.total_xp_earned = area_xp.get(area.name, 0)

    db.commit()


def seed_fitness_hub(db: Session) -> None:
    """Fitness Hub seed data (99-phase plan, Phases 41-42).

    Idempotent / append-only: muscle groups keyed on name, exercises on name,
    splits on (day_of_week, week_number, split_name), expenses on title,
    PRs on exercise_name, diet plans on title, and the user weight/membership
    fields are only filled when empty.
    """
    user = db.query(User).first()
    if not user:
        return

    # ── Phase 41: 12 muscle groups ──
    muscle_spec = [
        ("Calves", "Lower"), ("Shoulders", "Upper"), ("Chest", "Upper"),
        ("Abs", "Upper"), ("Back", "Upper"), ("Lower Back", "Lower"),
        ("Triceps", "Upper"), ("Glutes", "Lower"), ("Hamstring", "Lower"),
        ("Quads", "Lower"), ("Biceps", "Upper"), ("Forearms", "Upper"),
    ]
    existing_groups = {g.name: g for g in db.query(MuscleGroup).all()}
    for order, (name, part) in enumerate(muscle_spec):
        g = existing_groups.get(name)
        if g:
            g.sort_order = order
            continue
        db.add(MuscleGroup(
            name=name, body_part=part,
            image_3d_url=f"data:image/svg+xml,{_muscle_placeholder(name)}",
            sort_order=order, user_id=user.id,
        ))
    db.flush()

    # ── Phase 42a: exercises with sets/reps/weight per muscle group ──
    exercise_spec = {
        "Calves": [("Standing Calf Raise", 4, 15, 40)],
        "Shoulders": [("Overhead Press", 4, 8, 40), ("Lateral Raise", 3, 12, 8)],
        "Chest": [("Bench Press", 4, 8, 60), ("Incline Dumbbell Press", 3, 10, 20), ("Push-Ups", 3, 15, 0)],
        "Abs": [("Crunches", 3, 20, 0), ("Plank", 3, 1, 0)],
        "Back": [("Deadlift", 4, 6, 80), ("Lat Pulldown", 3, 10, 45)],
        "Lower Back": [("Back Extension", 3, 12, 0)],
        "Triceps": [("Tricep Pushdown", 3, 12, 15), ("Skull Crushers", 3, 10, 10)],
        "Glutes": [("Hip Thrust", 4, 10, 60)],
        "Hamstring": [("Romanian Deadlift", 4, 8, 50), ("Leg Curl", 3, 12, 25)],
        "Quads": [("Squat", 4, 8, 60), ("Leg Press", 3, 10, 120)],
        "Biceps": [("Barbell Curl", 3, 10, 20), ("Hammer Curl", 3, 10, 10)],
        "Forearms": [("Wrist Curl", 3, 15, 10)],
    }
    groups = {g.name: g for g in db.query(MuscleGroup).all()}
    existing_ex = {e.name: e for e in db.query(Exercise).all()}
    for gname, items in exercise_spec.items():
        g = groups.get(gname)
        if not g:
            continue
        for ex_name, sets, reps, weight in items:
            if ex_name in existing_ex:
                continue
            db.add(Exercise(
                name=ex_name, muscle_group_id=g.id,
                sets=sets, reps=reps, weight=weight, user_id=user.id,
            ))

    # ── Phase 42b: weekly PUSH/PULL/LEG splits (weeks 1 & 2) ──
    split_spec = [
        (0, "PUSH", ["Bench Press", "Overhead Press", "Tricep Pushdown", "Lateral Raise"]),
        (1, "PULL", ["Deadlift", "Lat Pulldown", "Barbell Curl", "Hammer Curl"]),
        (2, "LEG", ["Squat", "Romanian Deadlift", "Leg Press", "Calf Raise"]),
        (3, "PUSH", ["Incline Dumbbell Press", "Skull Crushers", "Front Raise"]),
        (4, "PULL", ["Barbell Row", "Pull-Up", "Face Pull", "Wrist Curl"]),
        (5, "LEG", ["Hip Thrust", "Leg Curl", "Bulgarian Split Squat"]),
    ]
    import json as _json
    existing_splits = {
        (s.day_of_week, s.week_number, s.split_name)
        for s in db.query(WorkoutSplit).all()
    }
    for week in (1, 2):
        for dow, split, exercises in split_spec:
            if (dow, week, split) in existing_splits:
                continue
            db.add(WorkoutSplit(
                day_of_week=dow, split_name=split,
                exercise_list=_json.dumps(exercises),
                week_number=week, user_id=user.id,
            ))

    # ── Phase 42c: 4 spec expenses ──
    expense_spec = [
        ("Protein & Creatine", 55.0, "Supplement"),
        ("Multivitamin", 12.0, "Supplement"),
        ("Liver Salt", 8.0, "Supplement"),
        ("Equipments", 150.0, "Equipment"),
    ]
    existing_expenses = {e.title: e for e in db.query(Expense).all()}
    today = date.today()
    for title, cost, cat in expense_spec:
        if title in existing_expenses:
            continue
        db.add(Expense(
            title=title, cost=cost, date=today - timedelta(days=2), category=cat, user_id=user.id,
        ))

    # ── Phase 42d: bench/overhead PRs ──
    pr_spec = [
        ("Bench Press", 60.0, 100.0, "kg"),
        ("Overhead Press", 40.0, 70.0, "kg"),
    ]
    existing_prs = {p.exercise_name: p for p in db.query(PersonalRecord).all()}
    for ex_name, cur, target, unit in pr_spec:
        if ex_name in existing_prs:
            continue
        db.add(PersonalRecord(
            exercise_name=ex_name, current_weight=cur,
            target_weight=target, unit=unit, user_id=user.id,
        ))

    # ── Phase 42e: 4 diet phases (Diet active) ──
    diet_spec = [
        ("Diet", True, 0),
        ("Bulking", False, 1),
        ("Cutting", False, 2),
        ("Maintenance", False, 3),
    ]
    existing_diets = {p.title: p for p in db.query(DietPlan).all()}
    for title, active, order in diet_spec:
        if title in existing_diets:
            continue
        db.add(DietPlan(
            title=title, is_active=active, sort_order=order, user_id=user.id,
        ))

    # ── Phase 42f: user weight-goal + membership (fill only when empty) ──
    if user.current_weight is None:
        user.initial_weight = 80.0
        user.current_weight = 78.5
        user.target_weight = 75.0
    if not user.membership_status or user.next_payment_date is None:
        user.membership_status = "Active"
        user.next_payment_date = today.replace(day=28) + timedelta(days=30)

    # ── Phase 42g: the 4 spec fitness habits + logs for heatmap fill ──
    spec_habits = [
        ("Workout", "Complete a workout session every day", "red"),
        ("3000 Kcal Diet", "Hit 3000 kcal every day", "green"),
        ("Drink 4L water", "Drink 4 liters of water every day", "blue"),
        ("Take all supplements", "Take protein, creatine, multivitamin daily", "orange"),
    ]
    habits = {h.name: h for h in db.query(Habit).all()}
    for name, goal, color in spec_habits:
        h = habits.get(name)
        if not h:
            h = Habit(
                name=name, description=goal, frequency="daily", target_count=1,
                color_theme=color, habit_type="good", xp_reward=30,
                current_streak=0, longest_streak=0, user_id=user.id,
            )
            db.add(h)
            db.flush()
            habits[name] = h
        h.goal = goal
        if not h.description:
            h.description = goal
        have = {str(l.date) for l in db.query(HabitLog).filter(HabitLog.habit_id == h.id).all()}
        for i in range(14):
            day = today - timedelta(days=i)
            if str(day) in have:
                continue
            if (i + h.id) % 5 == 0:
                continue  # some weak spots
            db.add(HabitLog(
                habit_id=h.id, date=day, completed=True, count=1,
                type="good", status="Completed", xp_change=h.xp_reward,
            ))

    db.commit()


def seed_mood(db: Session) -> None:
    """Mood tracking demo data (Zenith-Study-Planner G2, Phase 8).

    Idempotent / append-only: one entry per day for the last 7 days, keyed on
    (mood, energy, date) so re-seeding never duplicates.
    """
    from app.models.mood_log import MOODS

    user = db.query(User).first()
    if not user:
        return

    today = datetime.now().date()
    existing = {(m.mood, m.energy, m.logged_at.date()) for m in db.query(MoodLog).all()}

    # A believable week: focused high-energy study days + a stressed dip.
    pattern = [
        ("focused", 4, "Deep work session on algorithms"),
        ("focused", 5, "Great study flow"),
        ("stressed", 2, "Midterm pressure building"),
        ("relaxed", 3, "Recovered after a walk"),
        ("focused", 4, "Final revision sprint"),
        ("relaxed", 4, "Weekend reset"),
        ("focused", 3, "Prepared for the exam"),
    ]
    for i, (mood, energy, note) in enumerate(pattern):
        day = today - timedelta(days=6 - i)
        if (mood, energy, day) in existing:
            continue
        db.add(MoodLog(
            user_id=user.id, mood=mood, energy=energy, note=note,
            logged_at=datetime.combine(day, time(18, 0)),
        ))
    db.commit()


def seed_sleep(db: Session) -> None:
    """Sleep tracker demo data (Zenith-Study-Planner G3, Phase 15).

    Idempotent / append-only: one log per date for the last 7 nights, keyed on
    date so re-seeding never duplicates.
    """
    user = db.query(User).first()
    if not user:
        return

    today = datetime.now().date()
    existing_dates = {s.date for s in db.query(SleepLog).all()}

    # A believable week: mostly 7-8h nights with one short one.
    pattern = [
        ("23:00", "07:00", 4),
        ("23:30", "07:00", 3),
        ("00:30", "06:30", 2),  # short night
        ("22:45", "06:45", 4),
        ("23:15", "07:15", 4),
        ("23:45", "08:00", 4),
        ("23:00", "07:00", 5),
    ]
    for i, (bedtime, wake_time, quality) in enumerate(pattern):
        day = today - timedelta(days=6 - i)
        if day in existing_dates:
            continue
        db.add(SleepLog(
            user_id=user.id, date=day,
            bedtime=bedtime, wake_time=wake_time, quality=quality,
        ))
    db.commit()


def _muscle_placeholder(name: str) -> str:
    """Tiny inline SVG placeholder used as the 3D image URL for muscle groups."""
    import urllib.parse

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96">'
        f'<rect width="96" height="96" rx="12" fill="#1c1e21"/>'
        f'<text x="48" y="56" text-anchor="middle" font-size="26" font-family="sans-serif">💪</text>'
        f'<text x="48" y="82" text-anchor="middle" font-size="11" fill="#9aa0a6" font-family="sans-serif">{name}</text>'
        f'</svg>'
    )
    return urllib.parse.quote(svg)


def seed_character(db: Session, user: User) -> None:
    db.add(Character(
        user_id=user.id,
        name="Alex",
        class_name="Wizard",
        level=3,
        xp=1250,
        strength=6,
        agility=5,
        intelligence=8,
        endurance=4,
        current_quests=2,
    ))


def seed_rewards(db: Session, user: User) -> None:
    rewards = [
        ("Take a walk", "Enjoy a relaxing walk in the park", 50, "Lifestyle"),
        ("Dinner outside", "Treat yourself to dinner at your favorite restaurant", 200, "Food"),
        ("Take a day off", "Give yourself a full day of rest", 500, "Lifestyle"),
        ("Buy a game", "Purchase that game you've been eyeing", 1000, "Entertainment"),
    ]
    for title, desc, cost, cat in rewards:
        db.add(Reward(user_id=user.id, title=title, description=desc, xp_cost=cost, category=cat, is_available=True))


def seed_missions(db: Session, user: User) -> None:
    missions_data = [
        ("Notion Templates", "Create and share productivity templates for the team", "Productivity", "In Progress", 200),
        ("Content Creation", "Produce weekly blog posts and social media content", "Marketing", "Not Started", 300),
    ]
    quest_ids = [q.id for q in db.query(Quest).order_by(Quest.id).all()][:2]
    linked = ",".join(str(i) for i in quest_ids) if quest_ids else None
    for title, desc, mtype, status, xp in missions_data:
        mission = Mission(
            user_id=user.id, title=title, description=desc,
            mission_type=mtype, priority="High", status=status, xp_reward=xp,
            linked_quests=linked,
        )
        db.add(mission)
        db.flush()

        subtasks = [
            (f"Research {title}", False, 0),
            (f"Draft {title} outline", False, 1),
        ]
        if title == "Content Creation":
            subtasks.append(("Write first draft", False, 2))
        for st_title, completed, order in subtasks:
            db.add(MissionTask(mission_id=mission.id, title=st_title, completed=completed, sort_order=order))


def seed_schedule_events(db: Session, user: User) -> None:
    from datetime import time as dt_time
    events = [
        ("Morning Workout", 0, dt_time(7, 0), dt_time(7, 30), "fitness", 1, None),
        ("Team Standup", 0, dt_time(9, 0), dt_time(9, 15), "quest", 1, None),
        ("Deep Work Block", 0, dt_time(10, 0), dt_time(12, 0), "quest", None, "#ff9800"),
        ("Lunch Break", 0, dt_time(12, 0), dt_time(13, 0), None, None, None),
        ("Gym Session", 1, dt_time(18, 0), dt_time(19, 0), "fitness", None, "#4caf50"),
        ("Project Review", 1, dt_time(14, 0), dt_time(15, 0), "mission", 1, None),
        ("Reading Time", 2, dt_time(19, 0), dt_time(20, 0), None, None, "#2196f3"),
        ("Weekly Planning", 3, dt_time(10, 0), dt_time(11, 0), "quest", None, "#ff9800"),
        ("Course Study", 3, dt_time(14, 0), dt_time(16, 0), "mission", None, "#4caf50"),
        ("Journal Entry", 4, dt_time(21, 0), dt_time(21, 30), None, None, None),
        ("Movie Night", 5, dt_time(19, 0), dt_time(21, 0), None, None, None),
        ("Weekend Prep", 6, dt_time(10, 0), dt_time(11, 30), "quest", None, "#ff9800"),
    ]
    event_types = {
        "Morning Workout": ("health", "Home Gym"),
        "Team Standup": ("work", "Zoom"),
        "Deep Work Block": ("work", "Library"),
        "Lunch Break": ("social", "Campus Cafeteria"),
        "Gym Session": ("health", "City Gym"),
        "Project Review": ("work", "Lab 3"),
        "Reading Time": ("self", "Home"),
        "Weekly Planning": ("work", "Home Office"),
        "Course Study": ("class", "Study Hall"),
        "Journal Entry": ("self", "Home"),
        "Movie Night": ("social", "Living Room"),
        "Weekend Prep": ("work", "Home"),
    }
    for title, dow, start, end, ref_type, ref_id, color in events:
        etype, location = event_types.get(title, (None, None))
        db.add(ScheduleEvent(
            user_id=user.id, title=title, day_of_week=dow,
            start_time=start, end_time=end,
            event_type=etype, location=location,
            reference_type=ref_type, reference_id=ref_id, color=color,
        ))


def seed_life_areas(db: Session, user: User) -> None:
    areas = [
        ("Work", "Professional projects and career growth", 45.0, 0, 30, "In progress"),
        ("Fitness", "Physical health and exercise goals", 30.0, 1, 30, "In progress"),
        ("Self Development", "Learning, reading, and personal growth", 60.0, 2, 30, "In progress"),
        ("Health", "Mental well-being, sleep, and nutrition", 70.0, 3, 30, "In progress"),
    ]
    for name, desc, progress, order, target_days, status in areas:
        db.add(LifeArea(
            user_id=user.id, name=name, goal=desc,
            description=desc, progress_percent=progress,
            sort_order=order, target_days=target_days, status=status,
        ))


def seed_rpg_additions(db: Session) -> None:
    user = db.query(User).first()
    if not user:
        return
    # Gamification fields on the seeded user (append-only: only fill when empty).
    if not user.avatar_class:
        user.avatar_class = "Wizard"
    if not user.current_streak:
        user.current_streak = 3
    if not db.query(Character).filter(Character.user_id == user.id).first():
        seed_character(db, user)
    if not db.query(Reward).first():
        seed_rewards(db, user)
    existing_areas = db.query(LifeArea).count()
    if existing_areas < 4:
        # Only seed life areas if none exist (first boot or user deleted all).
        # Do NOT delete existing areas — respect user modifications.
        seed_life_areas(db, user)
    if not db.query(Mission).first():
        seed_missions(db, user)
    if not db.query(ScheduleEvent).first():
        seed_schedule_events(db, user)
    db.commit()


def seed_vault_habits(db: Session) -> None:
    """Seed the 4 vault habits with color themes + sample logs. Idempotent / append-only."""
    user = db.query(User).first()
    if not user:
        return

    vault_habits = [
        ("4 hr Deep Work", "Focused deep work sessions", "blue"),
        ("Eat Healthy", "Eat balanced, nutritious meals", "green"),
        ("Reading", "Daily reading habit", "orange"),
        ("Workout", "Daily exercise session", "red"),
    ]

    existing_names = {h.name for h in db.query(Habit).all()}
    new_habits = []
    for name, desc, color in vault_habits:
        if name in existing_names:
            continue
        h = Habit(
            name=name,
            description=desc,
            frequency="daily",
            target_count=1,
            color_theme=color,
            current_streak=3,
            longest_streak=3,
            user_id=user.id,
        )
        db.add(h)
        new_habits.append(h)

    if not new_habits:
        db.commit()
        return

    db.flush()
    # Sample logs: completed for the last 3 days for each new habit.
    today = date.today()
    for h in new_habits:
        for i in range(3):
            db.add(HabitLog(
                habit_id=h.id,
                date=today - timedelta(days=i),
                completed=True,
                count=1,
            ))
    db.commit()


def seed_vault_demo(db: Session) -> None:
    """Seed realistic vault demo data: projects with deadlines, project-linked
    tasks, and habit goals. Append-only and idempotent (Phase 91)."""
    user = db.query(User).first()
    if not user:
        return

    today = date.today()

    # -- A project with a near deadline ("7 Days to go" badge) + a completed one. --
    demo_projects = [
        ("Capstone Website", "Landing page + auth for the capstone demo", "In progress", 7),
        ("Study Guide Zine", "Print-ready revision guide for finals", "Completed", -3),
    ]
    existing_project_names = {p.name for p in db.query(Project).all()}
    for name, desc, status, days_offset in demo_projects:
        if name in existing_project_names:
            continue
        proj = Project(
            user_id=user.id,
            name=name,
            description=desc,
            status=status,
            deadline=today + timedelta(days=days_offset),
        )
        db.add(proj)
        existing_project_names.add(name)
        db.flush()

        # Project tasks drive the summary counts (total / incomplete).
        proj_tasks = [
            ("Write landing page copy", True),
            ("Set up auth flow", True),
            ("Responsive styling", False),
            ("Deploy to preview", False),
        ]
        if status == "Completed":
            proj_tasks = [(t, True) for t, _ in proj_tasks]
        for ptitle, pcompleted in proj_tasks:
            db.add(ProjectTask(project_id=proj.id, title=ptitle, completed=pcompleted))

    # -- Fresh tasks linked to a project (append-only: never re-parent existing rows). --
    capstone = db.query(Project).filter(Project.name == "Capstone Website").first()
    if capstone:
        linked_titles = {
            "Implement login page",
            "Write API tests",
            "Polish dashboard UI",
        }
        existing_titles = {t.title for t in db.query(Task).filter(Task.title.in_(linked_titles)).all()}
        for title in linked_titles - existing_titles:
            db.add(Task(
                title=title,
                subject_tag="Software",
                priority_tag="Medium",
                due_date=today + timedelta(days=5),
                status="Not started",
                project_id=capstone.id,
                user_id=user.id,
            ))

    # -- A task with no project (unrelated tab) and one with no due date (inbox). --
    if not db.query(Task).filter(Task.title == "Organize desk").first():
        db.add(Task(title="Organize desk", priority_tag="Low", status="Not started", user_id=user.id))
    if not db.query(Task).filter(Task.title == "Buy notebooks").first():
        db.add(Task(
            title="Buy notebooks",
            subject_tag="General",
            priority_tag="Low",
            due_date=None,
            status="Not started",
            user_id=user.id,
        ))

    # -- Habit goals: one per vault habit, with target dates. --
    vault_habit_names = ["4 hr Deep Work", "Eat Healthy", "Reading", "Workout"]
    habit_goal_titles = [
        "20 deep-work hours this month",
        "Cook 5 healthy meals a week",
        "Finish one book this quarter",
        "Work out 4x a week",
    ]
    existing_goal_titles = {g.title for g in db.query(Goal).all()}
    for habit_name, goal_title in zip(vault_habit_names, habit_goal_titles):
        if goal_title in existing_goal_titles:
            continue
        habit = db.query(Habit).filter(Habit.name == habit_name).first()
        if not habit:
            continue
        db.add(Goal(
            title=goal_title,
            quarter=f"Q{((today.month - 1) // 3) + 1}",
            progress_percentage=25.0,
            year=today.year,
            habit_id=habit.id,
            target_date=today + timedelta(days=21),
            is_completed=False,
        ))

    db.commit()
