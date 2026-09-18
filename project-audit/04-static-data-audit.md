# Static Data Audit

## Seed Data Analysis

The application uses a comprehensive seed system (`backend/app/seed/__init__.py`) that runs on first boot. The seed data is **idempotent and append-only** — it won't duplicate on re-runs.

### Seed Data Inventory

| Category | Count | Seeded Items |
|----------|-------|-------------|
| User | 1 | "Alex", Level 5, Wizard, 2340 XP |
| Courses | 5 | CS, OOP, Algorithms, Software, Data Structures |
| Assignments | 12 | 2-3 per course, mixed statuses |
| Exams | 5 | 1 per course |
| Goals | 4 | Quarterly goals with progress |
| Tasks | 8 | Various priorities and statuses |
| Habits | 14+ | 5 good, 5 bad, 4 vault habits, 3 legacy |
| Habit Logs | 50+ | 7-14 days per habit |
| Notes | 5 | 1 per course (short summaries) |
| Journal | 2 | Recent entries |
| Workouts | 3 | Running, Cycling, Yoga |
| Fitness Goals | 2 | Run 100km, 30 Workout Days |
| Quests | 2 | Master Algorithms, Fitness Challenge |
| Missions | 2 | Notion Templates, Content Creation |
| Projects | 3 | Capstone Website, Study Guide Zine + 1 legacy |
| Life Areas | 4 | Work, Fitness, Self Development, Health |
| Rewards | 8 | 4 original + 4 gamified |
| Schedule Events | 12 | Weekly recurring events |
| Flashcard Decks | 2 | Integration Techniques, Data Structures |
| Flashcards | 10 | 5+4 cards across decks |
| Grades | 6 | For first 2 courses |
| Study Plans | 1 | Biology Final |
| Mood Logs | 7 | 7-day pattern |
| Sleep Logs | 7 | 7-night pattern |
| Pomodoro Sessions | 7 | Various modes |
| Muscle Groups | 12 | Full body |
| Exercises | 20+ | Per muscle group |
| Workout Splits | 12 | 2 weeks × 6 days |
| Expenses | 4 | Supplement/equipment costs |
| Personal Records | 2 | Bench, Overhead Press |
| Diet Plans | 4 | Diet, Bulking, Cutting, Maintenance |

### Is Seed Data Appropriate?

**YES** — the seed data is **demo/first-boot data**, not fake production data. It:
- Runs only on first boot (`fresh = user is None`)
- Is idempotent (won't duplicate)
- Represents a realistic student's initial setup
- Can be deleted by the user (they can delete tasks, habits, etc.)

**However**, some seed data is problematic:
1. **Habits are re-seeded on every boot** (`seed_vault_habits`) — user deletions are resurrected
2. **Life Areas are re-seeded if count < 4** — user deletions may be resurrected
3. **Demo tasks/projects/goals** may confuse users who start fresh

## Frontend Hardcoded Data

### Acceptable Hardcoded Data
- Day names: `['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']`
- Mood emojis: `{ happy: '😊', neutral: '😐', ... }`
- Tab labels: `['Work', 'Fitness', 'Personal', ...]`
- Color themes: `{ blue: '...', green: '...', ... }`
- Status badges: computed from data, not hardcoded

### Problematic Hardcoded Data
1. **Dashboard stat tiles** — show 0 until API loads (no skeleton)
2. **Quest filter categories** — hardcoded: `['Work', 'Fitness', 'Personal', 'Learning', 'Social', 'Health']`
3. **Mood options** — hardcoded: `['happy', 'neutral', 'sad', 'anxious', 'excited']`
4. **Character class** — hardcoded as "Wizard" in seed
5. **User ID 1** — hardcoded throughout (`user_id: 1`)

### Mock/Demo Data Concerns

| Location | Issue | Severity |
|----------|-------|----------|
| `seed_vault_habits` | Re-seeded every boot, resurrects deletions | Medium |
| `seed_rpg_additions` | Re-seeds life areas if count < 4 | Medium |
| Dashboard stat tiles | Show 0 briefly (no loading skeleton) | Low |
| Quest filter categories | Hardcoded list, not from DB | Low |
| Character ID 1 | Hardcoded user_id | Low |

## Data That Should Be Dynamic

1. **Dashboard statistics** — already dynamic (from API), but loading state is missing
2. **Course counts** — from DB, but `current_assignment`/`total_assignments` may be stale
3. **Habit streaks** — recalculated from logs, but seed values persist
4. **XP/Level** — from DB, but seed values may not reflect actual activity
5. **Study plan weeks** — hardcoded in seed, but user can create new ones
6. **Grade weights** — seeded for first course, but user can add more

## Static Data That Should Be Removed or Made Dynamic

None identified — the seed data is appropriate for a demo/first-boot experience. The real issue is that some seed data **resurrects on boot** (vault habits, life areas), which should be fixed.
