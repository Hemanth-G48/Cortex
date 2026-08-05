"""Tests for the Grades/GPA feature (Groups 2)."""
from __future__ import annotations

from app.services import grade_calc


# ---------------------------------------------------------------------------
# grade_calc service (Phase 13) — mirrors Shiori's LETTER_GRADE / pctToGPA tables
# ---------------------------------------------------------------------------

def test_letter_grade_table():
    cases = [
        (93, "A"), (95, "A"), (90, "A-"), (87, "B+"), (83, "B"), (80, "B-"),
        (77, "C+"), (73, "C"), (70, "C-"), (67, "D+"), (63, "D"), (60, "D-"), (59, "F"), (0, "F"),
    ]
    for pct, expected in cases:
        assert grade_calc.letter_grade(pct) == expected, f"{pct} → {expected}"


def test_pct_to_gpa_table():
    cases = [
        (93, 4.0), (90, 3.7), (87, 3.3), (83, 3.0), (80, 2.7),
        (77, 2.3), (73, 2.0), (70, 1.7), (67, 1.3), (63, 1.0), (60, 0.7), (59, 0.0),
    ]
    for pct, expected in cases:
        assert grade_calc.pct_to_gpa(pct) == expected, f"{pct} → {expected}"


def test_calculate_unweighted():
    grades = [
        {"points_earned": 48, "points_possible": 50, "category_id": None},
        {"points_earned": 44, "points_possible": 50, "category_id": None},
    ]
    result = grade_calc.calculate_course_grade(grades)
    assert result is not None
    assert result["percentage"] == 92.0
    assert result["letter_grade"] == "A-"  # 90-92 → A-
    assert result["is_weighted"] is False
    assert result["total_earned"] == 92.0
    assert result["total_possible"] == 100.0


def test_calculate_weighted():
    grades = [
        {"points_earned": 48, "points_possible": 50, "category_id": 1},   # Homework 25%
        {"points_earned": 44, "points_possible": 50, "category_id": 1},
        {"points_earned": 18, "points_possible": 20, "category_id": 2},   # Quizzes 25%
        {"points_earned": 138, "points_possible": 150, "category_id": 3}, # Midterm 25%
    ]
    weights = [{"id": 1, "weight": 25}, {"id": 2, "weight": 25}, {"id": 3, "weight": 25}, {"id": 4, "weight": 25}]
    result = grade_calc.calculate_course_grade(grades, weights)
    assert result is not None
    assert result["is_weighted"] is True
    assert result["letter_grade"] == "A-"  # (92+90+92)/3 weighted → 91.3
    assert result["percentage"] == 91.3


def test_calculate_empty_and_zero():
    assert grade_calc.calculate_course_grade([]) is None
    assert grade_calc.calculate_course_grade([{"points_earned": 0, "points_possible": 0, "category_id": None}]) is None


def test_needed_on_final():
    # current 85, final worth 30%, want 90 → (90 - 85*0.7)/0.3 = 101.7
    assert grade_calc.needed_on_final(85, 30, 90) == 101.7
    # current 90, final worth 50%, want 90 → exactly 90
    assert grade_calc.needed_on_final(90, 50, 90) == 90.0


def test_cumulative_gpa():
    # 4.0 (93%) * 3 credits + 3.0 (83%) * 3 credits = 21 / 6 = 3.5
    assert grade_calc.cumulative_gpa([(95, 3), (83, 3)]) == 3.5
    assert grade_calc.cumulative_gpa([]) is None


# ---------------------------------------------------------------------------
# API endpoints (Phase 14)
# ---------------------------------------------------------------------------

def test_grade_crud(client):
    # List seeded grades
    resp = client.get("/api/grades")
    assert resp.status_code == 200
    grades = resp.json()
    assert len(grades) >= 5

    # Create
    resp = client.post("/api/grades", json={
        "course_id": grades[0]["course_id"], "title": "Pop Quiz", "points_earned": 9, "points_possible": 10,
    })
    assert resp.status_code == 200
    created = resp.json()
    assert created["id"]
    assert created["points_earned"] == 9

    # Update
    resp = client.put(f"/api/grades/{created['id']}", json={
        "course_id": created["course_id"], "title": "Pop Quiz v2", "points_earned": 10, "points_possible": 10,
    })
    assert resp.json()["points_earned"] == 10

    # Delete
    resp = client.delete(f"/api/grades/{created['id']}")
    assert resp.status_code == 200
    assert client.get("/api/grades/courses/{0}".format(created["course_id"])).status_code == 200


def test_course_grades_and_calculate(client):
    courses = client.get("/api/courses/").json()
    cid = courses[0]["id"]

    resp = client.post("/api/grades/calculate", json={"course_id": cid})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grade_count"] >= 4
    assert data["percentage"] is not None
    assert data["letter_grade"] in {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"}


def test_calculate_missing_course(client):
    resp = client.post("/api/grades/calculate", json={"course_id": 9999})
    assert resp.status_code == 404


def test_gpa_endpoint(client):
    resp = client.get("/api/grades/gpa")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gpa"] is not None
    assert isinstance(data["courses"], list)
    graded = [c for c in data["courses"] if c["percentage"] is not None]
    assert len(graded) >= 2


def test_needed_on_final_endpoint(client):
    resp = client.post("/api/grades/needed-on-final", json={"current_pct": 85, "final_weight_pct": 30, "desired_pct": 90})
    assert resp.status_code == 200
    assert resp.json()["needed_pct"] == 101.7


def test_weights_crud(client):
    courses = client.get("/api/courses/").json()
    cid = courses[0]["id"]

    resp = client.post("/api/grades/weights", json={"course_id": cid, "name": "Participation", "weight": 10})
    assert resp.status_code == 200
    weight = resp.json()
    assert weight["name"] == "Participation"

    resp = client.put(f"/api/grades/weights/{weight['id']}", json={"weight": 15})
    assert resp.json()["weight"] == 15

    resp = client.get(f"/api/grades/courses/{cid}/weights")
    assert any(w["name"] == "Participation" for w in resp.json())

    resp = client.delete(f"/api/grades/weights/{weight['id']}")
    assert resp.status_code == 200
