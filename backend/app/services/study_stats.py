"""Study analytics: per-course assignment completion and aggregated stats."""

from sqlalchemy.orm import Session

from app.models import Assignment, Course


def compute_assignment_analytics(db: Session, user_id: int) -> dict:
    """Return per-course assignment completion plus an overall summary.

    Assignments are course-scoped (the Assignment model has no user column);
    the user_id is honored for auth at the endpoint level.
    """
    assignments = db.query(Assignment).all()
    courses = {c.id: c.title for c in db.query(Course).all()}

    per_course: dict[int, dict] = {}
    for a in assignments:
        if a.course_id is None:
            continue
        bucket = per_course.setdefault(
            a.course_id,
            {"course_id": a.course_id, "course_title": courses.get(a.course_id, "General"), "total": 0, "done": 0},
        )
        bucket["total"] += 1
        if a.status == "Completed":
            bucket["done"] += 1

    rows = []
    for cid, b in per_course.items():
        b["done_ratio"] = round(b["done"] / b["total"], 2) if b["total"] > 0 else 0.0
        rows.append(b)
    rows.sort(key=lambda r: r["total"], reverse=True)

    total = len(assignments)
    done = sum(1 for a in assignments if a.status == "Completed")
    overall = {
        "total": total,
        "done": done,
        "completion_pct": round(done / total * 100, 1) if total > 0 else 0.0,
    }

    return {"per_course": rows, "overall": overall}
