"""Tests for the Fitness Hub endpoints (99-phase plan, Phase 98)."""

import pytest


class TestExercises:
    def test_list_exercises(self, client):
        resp = client.get("/api/exercises")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        assert "muscle_group_id" in data[0]
        assert "sets" in data[0]
        assert "reps" in data[0]
        assert "weight" in data[0]

    def test_filter_by_muscle_group(self, client):
        resp = client.get("/api/exercises?muscle_group_id=3")
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["muscle_group_id"] == 3 for e in data)

    def test_create_exercise(self, client):
        resp = client.post("/api/exercises", json={
            "name": "Test Curl", "muscle_group_id": 11,
            "sets": 3, "reps": 10, "weight": 12.5, "user_id": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Curl"
        assert data["sets"] == 3

    def test_update_exercise(self, client):
        resp = client.put("/api/exercises/1", json={
            "name": "Updated Press", "muscle_group_id": 3,
            "sets": 5, "reps": 5, "weight": 80.0, "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Press"
        assert resp.json()["sets"] == 5

    def test_delete_exercise(self, client):
        resp = client.delete("/api/exercises/1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestMuscleGroups:
    def test_list_12_groups(self, client):
        resp = client.get("/api/muscle-groups")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        names = {g["name"] for g in data}
        assert {"Chest", "Back", "Quads", "Biceps"} <= names

    def test_muscle_group_exercises(self, client):
        resp = client.get("/api/muscle-groups/3/exercises")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all(e["muscle_group_id"] == 3 for e in data)

    def test_create_muscle_group(self, client):
        resp = client.post("/api/muscle-groups", json={
            "name": "Neck", "body_part": "Upper", "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neck"

    def test_delete_muscle_group(self, client):
        resp = client.delete("/api/muscle-groups/1")
        assert resp.status_code == 200


class TestWorkoutSplits:
    def test_list_week_filter(self, client):
        week1 = client.get("/api/workout-splits?week_number=1")
        week2 = client.get("/api/workout-splits?week_number=2")
        assert week1.status_code == 200
        assert week2.status_code == 200
        assert len(week1.json()) == 6
        assert len(week2.json()) == 6
        assert all(s["week_number"] == 1 for s in week1.json())

    def test_create_split(self, client):
        resp = client.post("/api/workout-splits", json={
            "day_of_week": 6, "split_name": "REST",
            "exercise_list": '["Stretch"]', "week_number": 1, "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["day_of_week"] == 6


class TestExpenses:
    def test_list_expenses(self, client):
        resp = client.get("/api/expenses")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4
        titles = {e["title"] for e in data}
        assert {"Protein & Creatine", "Multivitamin"} <= titles

    def test_expense_summary(self, client):
        resp = client.get("/api/expenses/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_category" in data
        assert data["total"] > 0
        assert sum(data["by_category"].values()) == pytest.approx(data["total"])

    def test_create_expense(self, client):
        resp = client.post("/api/expenses", json={
            "title": "Gym Bag", "cost": 25.0,
            "date": "2026-08-01", "category": "Equipment", "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Gym Bag"

    def test_delete_expense(self, client):
        resp = client.delete("/api/expenses/1")
        assert resp.status_code == 200


class TestPersonalRecords:
    def test_list_records(self, client):
        resp = client.get("/api/personal-records")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        names = {r["exercise_name"] for r in data}
        assert {"Bench Press", "Overhead Press"} <= names

    def test_create_record(self, client):
        resp = client.post("/api/personal-records", json={
            "exercise_name": "Squat", "current_weight": 80.0,
            "target_weight": 120.0, "unit": "kg", "user_id": 1,
        })
        assert resp.status_code == 200
        assert resp.json()["target_weight"] == 120.0


class TestDietPlans:
    def test_list_plans(self, client):
        resp = client.get("/api/diet-plans")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        titles = {p["title"] for p in data}
        assert {"Diet", "Bulking", "Cutting", "Maintenance"} == titles

    def test_active_plan(self, client):
        resp = client.get("/api/diet-plans/active")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Diet"
        assert resp.json()["is_active"] is True

    def test_activate_switches(self, client):
        resp = client.put("/api/diet-plans/2", json={
            "title": "Bulking", "is_active": True, "sort_order": 1, "user_id": 1,
        })
        assert resp.status_code == 200
        active = client.get("/api/diet-plans/active").json()
        assert active["title"] == "Bulking"


class TestWeightGoal:
    def test_get_weight_goal(self, client):
        resp = client.get("/api/users/1/weight-goal")
        assert resp.status_code == 200
        data = resp.json()
        assert "initial" in data
        assert "current" in data
        assert "target" in data
        assert "percent" in data
        assert 0 <= data["percent"] <= 100

    def test_update_weight_goal(self, client):
        resp = client.put("/api/users/1/weight-goal", json={
            "initial_weight": 80.0, "current_weight": 78.0, "target_weight": 75.0,
        })
        assert resp.status_code == 200
        assert resp.json()["current"] == 78.0
        assert resp.json()["percent"] == pytest.approx(40.0, abs=0.1)


class TestMembership:
    def test_get_membership(self, client):
        resp = client.get("/api/users/1/membership")
        assert resp.status_code == 200
        data = resp.json()
        assert data["membership_status"] == "Active"
        assert "next_payment_date" in data
        assert isinstance(data["days_to_payment"], int)


class TestFitnessHubSummary:
    def test_summary_shape(self, client):
        resp = client.get("/api/fitness-hub/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "weight_goal" in data
        assert "pr_tracker" in data
        assert "membership" in data
        assert "diet_plans" in data
        assert "expenses_summary" in data
        assert "weekly_split" in data
        assert "muscle_groups" in data
        assert "spec_habits" in data

    def test_weekly_split_ordered(self, client):
        data = client.get("/api/fitness-hub/summary").json()
        week1 = data["weekly_split"]["1"]
        days = [d["day"] for d in week1]
        assert days == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        assert all(d["split_name"] in {"PUSH", "PULL", "LEG"} for d in week1)

    def test_muscle_groups_have_counts(self, client):
        data = client.get("/api/fitness-hub/summary").json()
        assert len(data["muscle_groups"]) == 12
        chest = next(g for g in data["muscle_groups"] if g["name"] == "Chest")
        assert chest["exercise_count"] >= 2

    def test_spec_habits_heatmap(self, client):
        data = client.get("/api/fitness-hub/summary").json()
        habits = data["spec_habits"]
        assert len(habits) >= 4
        for h in habits:
            assert len(h["heatmap_7x7"]) == 49
            assert h["days_completed"] > 0
            assert 0 <= h["percent"] <= 100


class TestHabitGoalField:
    def test_habit_goal_defaults_null(self, client):
        resp = client.get("/api/habits/1")
        assert resp.status_code == 200
        assert "goal" in resp.json()

    def test_update_habit_goal(self, client):
        resp = client.put("/api/habits/1/goal", json={"goal": "Work out 5x a week"})
        assert resp.status_code == 200
        assert resp.json()["goal"] == "Work out 5x a week"

    def test_goal_persists_on_get(self, client):
        client.put("/api/habits/1/goal", json={"goal": "Run 10km weekly"})
        resp = client.get("/api/habits/1")
        assert resp.json()["goal"] == "Run 10km weekly"
