"""Tests for the Gamified Habit Tracker module (99-phase plan, Groups 1-4).

Covers: habit_type filter + good/bad aliases, Did-Today aggregation, the
completed-habit calendar endpoint, the XP engine (award / penalty / streak /
days_caught), pomodoro session mode, life-area totals, the status-window and
summary endpoints, and reward-claim wallet consistency.
"""

from datetime import date

import pytest


TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# Habit type filtering (Phases 17-18)
# ---------------------------------------------------------------------------
def test_list_habits_type_filter(client):
    good = client.get("/api/habits?type=good").json()
    bad = client.get("/api/habits?type=bad").json()
    assert len(good) >= 1 and len(bad) >= 1
    assert all(h["habit_type"] == "good" for h in good)
    assert all(h["habit_type"] == "bad" for h in bad)


def test_good_and_bad_aliases(client):
    good = client.get("/api/habits/good").json()
    bad = client.get("/api/habits/bad").json()
    assert all(h["habit_type"] == "good" for h in good)
    assert all(h["habit_type"] == "bad" for h in bad)
    # Aliases agree with the filter endpoint.
    assert {h["id"] for h in good} == {h["id"] for h in client.get("/api/habits?type=good").json()}


def test_habit_exposes_xp_fields(client):
    habit = client.get("/api/habits/good").json()[0]
    for key in ("habit_type", "xp_reward", "xp_penalty", "image_url", "days_caught"):
        assert key in habit
    bad = client.get("/api/habits/bad").json()[0]
    assert bad["xp_penalty"] > 0


# ---------------------------------------------------------------------------
# Did-Today aggregation (Phase 19)
# ---------------------------------------------------------------------------
def test_habits_today(client):
    data = client.get("/api/habits/today").json()
    assert isinstance(data, list)
    item = data[0]
    for key in ("id", "name", "habit_type", "log_today", "xp_today", "status"):
        assert key in item
    # Seed writes logs for the last 7 days including today for some habits.
    assert any(i["log_today"] for i in data)


def test_habits_today_flags_after_log(client):
    good = client.get("/api/habits/good").json()[0]
    client.post("/api/habit-logs", json={"habit_id": good["id"], "date": TODAY, "completed": True})
    today = client.get("/api/habits/today").json()
    flagged = next(i for i in today if i["id"] == good["id"])
    assert flagged["log_today"] is True
    assert flagged["xp_today"] == good["xp_reward"]


# ---------------------------------------------------------------------------
# Calendar endpoint (Phase 20)
# ---------------------------------------------------------------------------
def test_habit_logs_calendar(client):
    resp = client.get("/api/habit-logs/calendar?type=good")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    day = data[0]
    assert "date" in day and "logs" in day
    assert all(l["habit_type"] == "good" for l in day["logs"])
    assert all("habit_name" in l and "xp_change" in l for l in day["logs"])


def test_habit_logs_calendar_type_filter(client):
    good = client.get("/api/habit-logs/calendar?type=good").json()
    bad = client.get("/api/habit-logs/calendar?type=bad").json()
    for group in good + bad:
        expected = "good" if group in good else "bad"
        assert all(l["habit_type"] == expected for l in group["logs"])


# ---------------------------------------------------------------------------
# Calendar reorder + sort_order (Phase 91)
# ---------------------------------------------------------------------------
def test_calendar_logs_carry_sort_order(client):
    data = client.get("/api/habit-logs/calendar?type=good").json()
    assert len(data) >= 1
    assert all("sort_order" in l for day in data for l in day["logs"])


def test_reorder_habit_logs(client):
    data = client.get("/api/habit-logs/calendar?type=good").json()
    # Find a day with at least two logs to reorder.
    target = next((d for d in data if len(d["logs"]) >= 2), None)
    assert target is not None, "expected a seeded day with 2+ good-habit logs"
    ids = [l["id"] for l in target["logs"]]
    swapped = list(reversed(ids))

    resp = client.post("/api/habit-logs/reorder", json={"log_ids": swapped})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["reordered"] == len(swapped)

    day = next(d for d in client.get("/api/habit-logs/calendar?type=good").json() if d["date"] == target["date"])
    assert [l["id"] for l in day["logs"]] == swapped


def test_reorder_unknown_log_404(client):
    resp = client.post("/api/habit-logs/reorder", json={"log_ids": [999999]})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# XP engine: award / penalty / streak / days_caught (Phases 10-13, 16)
# ---------------------------------------------------------------------------
def test_good_habit_awards_xp_and_bumps_streak(client):
    before = client.get("/api/characters/1").json()
    good = client.get("/api/habits/good").json()[0]
    streak_before = good["current_streak"]

    resp = client.post("/api/habit-logs", json={"habit_id": good["id"], "date": TODAY, "completed": True})
    assert resp.status_code == 200
    log = resp.json()
    assert log["type"] == "good"
    assert log["status"] == "Completed"
    assert log["xp_change"] == good["xp_reward"]

    after = client.get("/api/characters/1").json()
    assert after["xp"] == before["xp"] + good["xp_reward"]
    habit = client.get(f"/api/habits/{good['id']}").json()
    assert habit["current_streak"] == streak_before + 1


def test_good_habit_never_downgrades_level(client):
    # Seeded character is level 3 with 1250 XP; a habit completion must not
    # drop the level even though (xp + reward) // 1000 + 1 would compute 2.
    char = client.get("/api/characters/1").json()
    assert char["level"] == 3
    good = client.get("/api/habits/good").json()[0]
    client.post("/api/habit-logs", json={"habit_id": good["id"], "date": TODAY, "completed": True})
    after = client.get("/api/characters/1").json()
    assert after["xp"] == char["xp"] + good["xp_reward"]
    assert after["level"] == 3


def test_bad_habit_penalizes_xp_and_bumps_days_caught(client):
    before = client.get("/api/characters/1").json()
    bad = client.get("/api/habits/bad").json()[0]
    caught_before = bad["days_caught"]

    resp = client.post("/api/habit-logs", json={"habit_id": bad["id"], "date": TODAY, "completed": True})
    assert resp.status_code == 200
    log = resp.json()
    assert log["type"] == "bad"
    assert log["status"] == "Shit I did it"
    assert log["xp_change"] == -bad["xp_penalty"]

    after = client.get("/api/characters/1").json()
    assert after["xp"] == before["xp"] - bad["xp_penalty"]
    habit = client.get(f"/api/habits/{bad['id']}").json()
    assert habit["days_caught"] == caught_before + 1


def test_xp_never_negative(client):
    client.put("/api/characters/1", json={
        "name": "Alex", "class_name": "Wizard", "level": 1, "xp": 5,
        "strength": 6, "agility": 5, "intelligence": 8, "endurance": 4,
    })
    bad = client.get("/api/habits/bad").json()[0]
    for _ in range(3):
        client.post("/api/habit-logs", json={"habit_id": bad["id"], "date": TODAY, "completed": True})
    char = client.get("/api/characters/1").json()
    assert char["xp"] == 0


def test_uncompleted_log_does_not_award_xp(client):
    before = client.get("/api/characters/1").json()
    good = client.get("/api/habits/good").json()[0]
    resp = client.post("/api/habit-logs", json={"habit_id": good["id"], "date": TODAY, "completed": False})
    assert resp.status_code == 200
    assert resp.json()["xp_change"] == 0
    assert client.get("/api/characters/1").json()["xp"] == before["xp"]


# ---------------------------------------------------------------------------
# Habit tracker endpoints (Phases 21-23)
# ---------------------------------------------------------------------------
def test_status_window(client):
    resp = client.get("/api/habit-tracker/status-window")
    assert resp.status_code == 200
    data = resp.json()
    assert data["character"] is not None
    assert data["xp_to_next"] is not None
    assert "today_habits" in data


def test_summary(client):
    resp = client.get("/api/habit-tracker/summary")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("total_xp", "level", "current_streak", "good_today", "bad_today", "xp_to_next",
                "good_count", "bad_count", "life_areas", "rewards_available"):
        assert key in data
    assert data["good_count"] >= 1
    assert data["bad_count"] >= 1
    for area in data["life_areas"]:
        assert "total_xp_earned" in area
    for reward in data["rewards_available"]:
        assert "xp_cost" in reward


# ---------------------------------------------------------------------------
# Pomodoro mode (Phase 6)
# ---------------------------------------------------------------------------
def test_pomodoro_session_mode(client):
    resp = client.post("/api/pomodoro-sessions", json={
        "user_id": 1,
        "start_time": "2026-08-02T10:00:00",  # fixed past timestamp is fine for a session record
        "duration_minutes": 25,
        "completed": True,
        "mode": "Focus",
    })
    assert resp.status_code == 200
    assert resp.json()["mode"] == "Focus"
    sessions = client.get("/api/pomodoro-sessions").json()
    assert any(s["mode"] == "Focus" for s in sessions)


# ---------------------------------------------------------------------------
# Life-area totals (Phase 7)
# ---------------------------------------------------------------------------
def test_life_area_total_xp(client):
    areas = client.get("/api/life-areas").json()
    assert all("total_xp_earned" in a for a in areas)
    assert any(a["total_xp_earned"] > 0 for a in areas)


# ---------------------------------------------------------------------------
# Reward claim shares the same wallet as habit XP (Phase 24)
# ---------------------------------------------------------------------------
def test_reward_claim_deducts_user_total_xp(client):
    user_before = client.post("/api/auth/login").json()["user"]["total_xp"]
    created = client.post("/api/rewards", json={
        "user_id": 1, "title": "Wallet Check", "xp_cost": 100, "category": "Test",
    }).json()
    client.post(f"/api/rewards/{created['id']}/claim?user_id=1")
    user_after = client.post("/api/auth/login").json()["user"]["total_xp"]
    assert user_after == user_before - 100


# ---------------------------------------------------------------------------
# Habit-log partial update preserves type/status/xp_change (audit regression)
# ---------------------------------------------------------------------------
def test_habit_log_partial_update_preserves_semantics(client):
    """Editing only count/completed must not reset type/status/xp_change."""
    created = client.post("/api/habit-logs", json={
        "habit_id": 1, "date": "2026-08-02", "completed": True,
    }).json()
    log_id = created["id"]
    # A good habit: type=good, status=Completed, xp_change=+reward (30).
    assert created["type"] == "good"
    assert created["xp_change"] == 30

    resp = client.put(f"/api/habit-logs/{log_id}", json={"count": 3, "completed": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    # Semantics must survive the partial update.
    assert data["type"] == "good"
    assert data["status"] == "Completed"
    assert data["xp_change"] == 30


# ---------------------------------------------------------------------------
# Quest completion credits the shared wallet (audit regression)
# ---------------------------------------------------------------------------
def test_quest_complete_updates_user_wallet(client):
    """Completing a quest must credit both char.xp and user.total_xp."""
    before = client.post("/api/auth/login").json()["user"]["total_xp"]
    quest_xp = next(q for q in client.get("/api/quests").json() if q["id"] == 1)["xp_reward"]
    client.post("/api/quests/1/complete")
    after = client.post("/api/auth/login").json()["user"]["total_xp"]
    assert after == before + quest_xp
