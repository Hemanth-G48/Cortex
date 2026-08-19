"""End-to-end owner flow (single-user app): create course -> create assignment
-> student (owner) completes it -> analytics reflect completion.

The application is single-user and tokenless: one owner drives the whole loop
against the TestClient. This replaces the old cross-role teacher-broadcast
e2e while preserving the same integration coverage (course -> assignment ->
completion -> stats visibility).
"""

from app.models import Course


def test_owner_completes_assignment_analytics_reflect_it(client, db_session):
    # --- Owner creates a course ---
    course_resp = client.post(
        "/api/courses/",
        json={"title": "Linear Algebra", "status": "In progress"},
    )
    assert course_resp.status_code == 200, course_resp.json()
    course_id = course_resp.json()["id"]

    course = db_session.query(Course).filter(Course.id == course_id).first()
    assert course is not None
    assert course.title == "Linear Algebra"

    # --- Owner creates an assignment attached to that course ---
    assign_resp = client.post(
        "/api/assignments",
        json={
            "title": "Chapter 5 Problems",
            "description": "Complete odd-numbered problems",
            "type": "Homework",
            "status": "Not started",
            "due_date": "2026-08-15",
            "course_id": course_id,
        },
    )
    assert assign_resp.status_code == 200, assign_resp.json()
    assignment_id = assign_resp.json()["id"]
    assert assign_resp.json()["status"] == "Not started"

    # --- Owner completes the assignment ---
    complete = client.post(f"/api/assignments/{assignment_id}/complete")
    assert complete.status_code == 200
    assert complete.json()["status"] == "Completed"

    # --- Analytics reflect the completion ---
    analytics = client.get("/api/assignments/analytics").json()
    assert analytics["overall"]["total"] >= 1
    assert analytics["overall"]["done"] >= 1
    per_course = {c["course_id"]: c for c in analytics["per_course"]}
    assert course_id in per_course
    assert per_course[course_id]["done"] >= 1
