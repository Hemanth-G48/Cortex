"""Tests for assignments, exams, notes, goals, auth and all other endpoints."""

import pytest


class TestAuth:
    def test_login_returns_user(self, client):
        resp = client.post("/api/auth/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert data["user"]["name"] == "Alex"
        assert data["user"]["current_level"] == 5
        assert data["user"]["total_xp"] == 2340


class TestAssignments:
    def test_list_assignments(self, client):
        resp = client.get("/api/assignments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_list_by_course(self, client):
        resp = client.get("/api/courses/1/assignments")
        assert resp.status_code == 200
        data = resp.json()
        assert all(a["course_id"] == 1 for a in data)

    def test_create_assignment(self, client):
        resp = client.post("/api/assignments", json={
            "title": "Test Assignment",
            "course_id": 1,
            "due_date": "2026-08-01",
            "status": "Not started",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Assignment"

    def test_update_assignment(self, client):
        resp = client.put("/api/assignments/1", json={
            "title": "Updated Assignment",
            "course_id": 1,
            "due_date": "2026-08-01",
            "status": "Completed",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"


class TestExams:
    def test_list_exams(self, client):
        resp = client.get("/api/exams")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_list_by_course(self, client):
        resp = client.get("/api/courses/1/exams")
        assert resp.status_code == 200
        assert all(e["course_id"] == 1 for e in resp.json())

    def test_create_exam(self, client):
        resp = client.post("/api/exams", json={
            "title": "Final Exam",
            "course_id": 1,
            "date": "2026-12-15",
            "status": "Not started",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Final Exam"


class TestNotes:
    def test_list_notes(self, client):
        resp = client.get("/api/notes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_list_by_course(self, client):
        resp = client.get("/api/courses/1/notes")
        assert resp.status_code == 200
        assert all(n["course_id"] == 1 for n in resp.json())

    def test_create_note(self, client):
        resp = client.post("/api/notes", json={
            "title": "Test Note",
            "course_id": 1,
            "content": "Test content",
            "created_date": "2026-07-29",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Note"

    def test_update_note(self, client):
        resp = client.put("/api/notes/1", json={
            "title": "Updated Note",
            "course_id": 1,
            "content": "Updated content",
            "created_date": "2026-07-29",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Note"


class TestGoals:
    def test_list_goals(self, client):
        resp = client.get("/api/goals")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_create_goal(self, client):
        resp = client.post("/api/goals", json={
            "title": "New Goal",
            "quarter": "Q3",
            "progress_percentage": 0.0,
            "year": 2026,
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Goal"

    def test_update_goal(self, client):
        resp = client.put("/api/goals/1", json={
            "title": "Updated Goal",
            "quarter": "Q1",
            "progress_percentage": 100.0,
            "year": 2026,
        })
        assert resp.status_code == 200
        assert resp.json()["progress_percentage"] == 100.0


class TestPomodoro:
    def test_list_sessions(self, client):
        resp = client.get("/api/pomodoro-sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_session(self, client):
        resp = client.post("/api/pomodoro-sessions", json={
            "user_id": 1,
            "start_time": "2026-07-29T10:00:00",
            "duration_minutes": 25,
            "completed": True,
        })
        assert resp.status_code == 200
        assert resp.json()["duration_minutes"] == 25


class TestFitness:
    def test_list_workouts(self, client):
        resp = client.get("/api/workouts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_workout(self, client):
        resp = client.post("/api/workouts", json={
            "user_id": 1,
            "date": "2026-07-29",
            "type": "Running",
            "duration_minutes": 30,
            "calories": 250,
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "Running"

    def test_list_fitness_goals(self, client):
        resp = client.get("/api/fitness-goals")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_fitness_goal(self, client):
        resp = client.post("/api/fitness-goals", json={
            "user_id": 1,
            "name": "Test Goal",
            "target": 100.0,
            "current": 20.0,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Goal"

    def test_update_fitness_goal(self, client):
        resp = client.put("/api/fitness-goals/1", json={
            "user_id": 1,
            "name": "Updated Goal",
            "target": 100.0,
            "current": 50.0,
        })
        assert resp.status_code == 200
        assert resp.json()["current"] == 50.0


class TestJournal:
    def test_list_entries(self, client):
        resp = client.get("/api/journal-entries")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_entry(self, client):
        resp = client.post("/api/journal-entries", json={
            "user_id": 1,
            "date": "2026-07-29",
            "content": "Test journal entry",
            "mood": "happy",
        })
        assert resp.status_code == 200
        assert resp.json()["content"] == "Test journal entry"


class TestQuests:
    def test_list_quests(self, client):
        resp = client.get("/api/quests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_quest(self, client):
        resp = client.post("/api/quests", json={
            "user_id": 1,
            "title": "New Quest",
            "xp_reward": 100,
            "status": "Not started",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Quest"

    def test_update_quest(self, client):
        resp = client.put("/api/quests/1", json={
            "user_id": 1,
            "title": "Updated Quest",
            "xp_reward": 300,
            "status": "Completed",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"

    def test_list_quest_tasks(self, client):
        resp = client.get("/api/quests/1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_quest_task(self, client):
        resp = client.post("/api/quest-tasks", json={
            "quest_id": 1,
            "title": "Sub task",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Sub task"


class TestProjects:
    def test_list_projects(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_project(self, client):
        resp = client.post("/api/projects", json={
            "user_id": 1,
            "name": "New Project",
            "status": "Not started",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Project"

    def test_update_project(self, client):
        resp = client.put("/api/projects/1", json={
            "user_id": 1,
            "name": "Updated Project",
            "status": "Completed",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "Completed"

    def test_list_project_tasks(self, client):
        resp = client.get("/api/projects/1/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_project_task(self, client):
        resp = client.post("/api/project-tasks", json={
            "project_id": 1,
            "title": "Project task",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Project task"


class TestLifeAreas:
    def test_list_life_areas(self, client):
        resp = client.get("/api/life-areas")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_life_area(self, client):
        resp = client.post("/api/life-areas", json={
            "user_id": 1,
            "name": "Career",
            "satisfaction_score": 5,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Career"

    def test_update_life_area(self, client):
        resp = client.put("/api/life-areas/1", json={
            "user_id": 1,
            "name": "Updated Area",
            "satisfaction_score": 9,
        })
        assert resp.status_code == 200
        assert resp.json()["satisfaction_score"] == 9
