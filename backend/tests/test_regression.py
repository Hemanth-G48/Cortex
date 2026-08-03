"""Regression tests (Phases 92-93): original routers not covered elsewhere plus
new vault endpoints (habit archive/unarchive, goal complete, vault tab semantics)."""


# ---------------------------------------------------------------------------
# Phase 92: daily quests (original router)
# ---------------------------------------------------------------------------
class TestDailyQuests:
    def test_get_or_create_daily_quests(self, client):
        resp = client.get("/api/daily-quests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all(q["category"] == "Daily" for q in data)

    def test_daily_quests_idempotent(self, client):
        first = client.get("/api/daily-quests").json()
        second = client.get("/api/daily-quests").json()
        assert len(second) == len(first)
        assert [q["title"] for q in second] == [q["title"] for q in first]


# ---------------------------------------------------------------------------
# Phase 92: weekly reset (original router)
# ---------------------------------------------------------------------------
class TestWeeklyReset:
    def test_weekly_reset_creates_quests(self, client):
        resp = client.post("/api/weekly-reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["quests_created"] == 3
        assert "message" in data

    def test_weekly_reset_creates_weekly_quests(self, client):
        resp = client.post("/api/weekly-reset")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        # Weekly quests are persisted with the upcoming week's monday date.
        quests = client.get("/api/quests?category=Weekly").json()
        assert len(quests) == 3


# ---------------------------------------------------------------------------
# Phase 93: habit archive / unarchive
# ---------------------------------------------------------------------------
class TestHabitArchive:
    def test_archive_habit(self, client):
        resp = client.post("/api/habits/1/archive")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_archived"] is True

    def test_archive_excludes_from_default_list(self, client):
        client.post("/api/habits/1/archive")
        resp = client.get("/api/habits")
        assert resp.status_code == 200
        data = resp.json()
        assert all(h["is_archived"] is False for h in data)

    def test_archive_included_when_requested(self, client):
        client.post("/api/habits/1/archive")
        resp = client.get("/api/habits?include_archived=true")
        assert resp.status_code == 200
        data = resp.json()
        assert any(h["id"] == 1 and h["is_archived"] for h in data)

    def test_unarchive_habit(self, client):
        client.post("/api/habits/1/archive")
        resp = client.post("/api/habits/1/unarchive")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_archived"] is False

    def test_archive_not_found(self, client):
        resp = client.post("/api/habits/9999/archive")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Phase 93: goal complete toggle
# ---------------------------------------------------------------------------
class TestGoalComplete:
    def test_complete_goal(self, client):
        resp = client.post("/api/goals/1/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_completed"] is True
        assert data["progress_percentage"] == 100.0

    def test_goal_complete_not_found(self, client):
        resp = client.post("/api/goals/9999/complete")
        assert resp.status_code == 404

    def test_goal_list_filters_by_habit(self, client):
        # Pick a habit that actually has a linked goal from the seed, then filter.
        goals = client.get("/api/goals").json()
        linked = [g for g in goals if g["habit_id"] is not None]
        assert len(linked) >= 1
        habit_id = linked[0]["habit_id"]
        resp = client.get(f"/api/goals?habit_id={habit_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all(g["habit_id"] == habit_id for g in data)


# ---------------------------------------------------------------------------
# Phase 93: vault tab semantics
# ---------------------------------------------------------------------------
class TestVaultTabs:
    def test_vault_tab_completed(self, client):
        resp = client.get("/api/vault/tasks?tab=completed")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "Completed" for t in data)

    def test_vault_tab_unrelated_has_no_project(self, client):
        resp = client.get("/api/vault/tasks?tab=unrelated")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["project_id"] is None for t in data)

    def test_vault_tab_inbox_has_no_due_date(self, client):
        resp = client.get("/api/vault/tasks?tab=inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["due_date"] is None for t in data)
