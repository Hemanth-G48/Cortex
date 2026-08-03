"""Tests for the Gamified Quest Centre (Phases 93–94).

Covers the quest-centre aggregation endpoints (status-window, progress,
priority-window, quick-actions, life-areas, calendar, gamification) plus the
new streak / life-area-complete / mission-linked behaviors added for the spec.
"""


# ── Aggregation endpoints ──


def test_status_window_shape(client):
    res = client.get("/api/quest-centre/status-window")
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"character", "xp_to_next", "today_tasks"}
    char = data["character"]
    assert char["avatar_class"] == "Wizard"  # seeded gamification field
    assert char["current_streak"] == 3
    assert char["name"] == "Alex"
    assert char["class_name"] == "Wizard"
    assert isinstance(data["today_tasks"], list)
    # Character xp is 1250 → 250 XP into level 3, 750 XP to the next level.
    assert data["xp_to_next"] == 750


def test_status_window_today_tasks_include_due_today(client, db_session):
    from datetime import date, timedelta
    from app.models import Quest, User
    user = db_session.query(User).first()
    due = date.today()
    db_session.add(Quest(user_id=user.id, title="Due today quest", xp_reward=25, due_date=due))
    db_session.add(Quest(user_id=user.id, title="Due tomorrow", xp_reward=25, due_date=due + timedelta(days=1)))
    db_session.commit()

    res = client.get("/api/quest-centre/status-window")
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()["today_tasks"]]
    assert "Due today quest" in titles
    assert "Due tomorrow" not in titles


def test_progress_endpoint(client):
    res = client.get("/api/quest-centre/progress")
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"year", "month", "week", "day"}
    for key, value in data.items():
        assert isinstance(value, int)
        assert 0 <= value <= 100


def test_priority_window_buckets(client):
    res = client.get("/api/quest-centre/priority-window")
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"High", "Medium", "Low"}

    all_items = data["High"] + data["Medium"] + data["Low"]
    assert all_items, "priority window should contain open quests/tasks"
    for item in all_items:
        assert set(item) == {"title", "time_estimate", "id", "kind"}
        assert item["kind"] in {"quest", "task"}
    # Two open seeded quests default to Medium priority → a quest item exists.
    kinds = {i["kind"] for i in data["Medium"]}
    assert "quest" in kinds


def test_quick_actions(client):
    res = client.get("/api/quest-centre/quick-actions")
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) == 4
    kinds = {a["kind"] for a in actions}
    assert kinds == {"quest", "mission", "life_area", "reward"}
    for a in actions:
        assert a["label"] and a["route"]


def test_quest_centre_life_areas(client):
    res = client.get("/api/quest-centre/life-areas")
    assert res.status_code == 200
    areas = res.json()
    assert len(areas) == 4  # Work / Fitness / Self Development / Health
    for area in areas:
        assert area["target_days"] == 30
        assert area["status"] == "In progress"
        # Seeded today → days since creation is 0 (or 1 at a midnight boundary).
        assert area["complete_in_days"] in (29, 30)
        assert area["progress_percent"] in (45.0, 30.0, 60.0, 70.0)


def test_life_area_complete(client):
    res = client.post("/api/life-areas/1/complete")
    assert res.status_code == 200
    area = res.json()
    assert area["status"] == "Completed"
    assert area["progress_percent"] == 100.0

    # Reflected in the quest-centre life-areas aggregation.
    areas = client.get("/api/quest-centre/life-areas").json()
    completed = next(a for a in areas if a["id"] == 1)
    assert completed["status"] == "Completed"
    assert completed["complete_in_days"] == 0


def test_life_area_complete_missing(client):
    res = client.post("/api/life-areas/9999/complete")
    assert res.status_code == 404


def test_quest_centre_calendar(client):
    res = client.get("/api/quest-centre/calendar")
    assert res.status_code == 200
    data = res.json()
    assert set(data) == {"quests_by_date", "schedule_events"}

    # Seeded "Master Algorithms" has a due date in ~2 weeks → grouped.
    by_date = data["quests_by_date"]
    assert by_date, "at least one quest has a due date"
    for group in by_date:
        assert "date" in group and isinstance(group["quests"], list)
        for q in group["quests"]:
            assert {"id", "title", "status", "priority", "category", "xp_reward"} <= set(q)

    # 12 weekly schedule events seeded.
    assert len(data["schedule_events"]) == 12
    for e in data["schedule_events"]:
        assert "day_of_week" in e and "start_time" in e


def test_gamification_default_profile(client):
    res = client.get("/api/quest-centre/gamification")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["name"] == "Alex"
    assert data["avatar_class"] == "Wizard"
    assert data["current_streak"] == 3
    assert data["current_level"] == 5
    assert data["total_xp"] == 2340


def test_gamification_by_id(client):
    res = client.get("/api/quest-centre/gamification", params={"user_id": 1})
    assert res.status_code == 200
    assert res.json()["id"] == 1

    res = client.get("/api/quest-centre/gamification", params={"user_id": 9999})
    assert res.status_code == 404


# ── Streak behavior on quest completion (Phase 18) ──


def _complete(client, quest_id):
    return client.post(f"/api/quests/{quest_id}/complete")


def test_quest_complete_streak_starts_at_one(client):
    """No prior completed quest → completing resets the streak to 1."""
    res = _complete(client, 1)
    assert res.status_code == 200
    assert res.json()["status"] == "Completed"

    profile = client.get("/api/quest-centre/gamification").json()
    assert profile["current_streak"] == 1


def test_quest_complete_streak_increments_same_day(client):
    """Completing again on the same day increments the streak."""
    assert _complete(client, 1).status_code == 200
    assert _complete(client, 2).status_code == 200

    profile = client.get("/api/quest-centre/gamification").json()
    assert profile["current_streak"] == 2


def test_quest_complete_awards_xp(client):
    """Completing a quest adds its XP to the character."""
    res = _complete(client, 1)
    assert res.status_code == 200
    char = client.get("/api/characters/1").json()
    assert char["xp"] == 1250 + 200


def test_quest_complete_missing(client):
    res = client.post("/api/quests/9999/complete")
    assert res.status_code == 404


# ── Mission ↔ quest linking (Phase 20) ──


def test_mission_linked_quests(client):
    res = client.get("/api/missions/1/linked")
    assert res.status_code == 200
    quests = res.json()
    assert len(quests) == 2
    assert [q["id"] for q in quests] == [1, 2]
    assert all(q["user_id"] == 1 for q in quests)


def test_mission_linked_quests_empty(client, db_session):
    from app.models import Mission, User
    user = db_session.query(User).first()
    db_session.add(Mission(user_id=user.id, title="Unlinked mission", linked_quests=None))
    db_session.commit()
    mission = db_session.query(Mission).filter(Mission.title == "Unlinked mission").first()

    res = client.get(f"/api/missions/{mission.id}/linked")
    assert res.status_code == 200
    assert res.json() == []


def test_mission_linked_missing(client):
    res = client.get("/api/missions/9999/linked")
    assert res.status_code == 404
