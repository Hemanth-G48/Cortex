import json
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assignment, Course, CourseGapAnalysis, User
from app.schemas.course import CourseCreate, CourseResponse
from app.services import classroom_sync
from app.services.course_content import (
    course_content,
    course_document_count,
    course_documents,
    course_gaps,
)
from app.services.course_derivation import (
    course_sync_status,
    derive_courses_from_tags,
    list_course_resources,
)
from app.services.kb.gap_history import (
    delete_course_history,
    list_gap_history,
    record_gap_history,
)
from app.services.users import current_user

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _attach_progress(db: Session, courses: list[Course]) -> list[Course]:
    """Set transient progress_percentage from assignment completion.

    Progress is computed (done/total assignments per course) rather than
    trusting the stored current_assignment counters.
    """
    course_ids = [c.id for c in courses]
    rows = (
        db.query(Assignment.course_id)
        .filter(Assignment.course_id.in_(course_ids))
        .all()
    )
    total_by_course: dict[int, int] = {}
    for (cid,) in rows:
        total_by_course[cid] = total_by_course.get(cid, 0) + 1
    done_by_course: dict[int, int] = {}
    done_rows = (
        db.query(Assignment.course_id)
        .filter(Assignment.course_id.in_(course_ids), Assignment.status == "Completed")
        .all()
    )
    for (cid,) in done_rows:
        done_by_course[cid] = done_by_course.get(cid, 0) + 1

    for course in courses:
        total = total_by_course.get(course.id, 0)
        done = done_by_course.get(course.id, 0)
        course.progress_percentage = round(done / total * 100, 1) if total > 0 else 0.0
        # Audit defect #79: counters are derived from the Assignment table on
        # every read instead of trusting the stored (possibly stale) columns.
        course.total_assignments = total
        course.current_assignment = done
    return courses


@router.get("/", response_model=List[CourseResponse])
def list_courses(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Single-owner app: scoped to the owner (kept for data hygiene).
    courses = db.query(Course).filter(Course.user_id == current_user.id).all()
    return _attach_progress(db, courses)


# NOTE: registered before "/{course_id}" so "resources"/"sync-status" are not parsed as ids.
@router.get("/sync-status")
def courses_sync_status(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Health payload explaining why a KB sync may be empty (sources/docs/tags
    counts + last-run diagnostics + Google state).
    """
    return course_sync_status(db, current_user.id)


# NOTE: registered before "/{course_id}" so "resources" is not parsed as an id.
@router.get("/resources")
def course_resources(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    """Resource cards for the Academic Resources grid (KB folders + Classroom)."""
    return list_course_resources(db, current_user.id)


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.id)
        .first()
    )
    if not course:
        raise HTTPException(404, "Course not found")
    return _attach_progress(db, [course])[0]


def _course_or_404(db: Session, user_id: int, course_id: int) -> Course:
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == user_id)
        .first()
    )
    if not course:
        raise HTTPException(404, "Course not found")
    return course


@router.post("/", response_model=CourseResponse)
def create_course(data: CourseCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["user_id"] = current_user(db).id
    course = Course(**payload)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    data: CourseCreate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.id)
        .first()
    )
    if not course:
        raise HTTPException(404, "Course not found")
    payload = data.model_dump(exclude_unset=True)
    # Ownership is not editable via the API in the single-user app.
    payload.pop("user_id", None)
    for key, val in payload.items():
        setattr(course, key, val)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.id)
        .first()
    )
    if not course:
        raise HTTPException(404, "Course not found")
    # Drop the saved Gap Analysis AND its history — neither may outlive the
    # course (the cache would dangle; the history would reference a ghost).
    _invalidate_saved_gaps(db, current_user.id, course.id)
    delete_course_history(db, current_user.id, course.id)
    db.delete(course)
    db.commit()
    return {"ok": True}


@router.get("/{course_id}/documents")
def course_documents_endpoint(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
    """Get Second Brain documents tagged with this course's subject."""
    course = _course_or_404(db, current_user.id, course_id)
    return course_documents(db, current_user.id, course)


@router.get("/{course_id}/content")
def course_content_endpoint(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Subject Details payload: Second Brain (documents, nested topics,
    related concepts, subject-scoped knowledge graph) + Classroom content.
    """
    course = _course_or_404(db, current_user.id, course_id)
    return course_content(db, current_user.id, course)


def _load_saved_gaps(db: Session, user_id: int, course: Course) -> dict[str, Any] | None:
    """Return a previously saved analysis payload, or None.

    When the saved copy exists, also computes ``new_notes_since_analysis``: how
    many Second Brain documents were added to this subject after the analysis
    was computed (0 when none) — lets the UI surface staleness next to the
    cached notice instead of silently reusing an outdated result.
    """
    saved = (
        db.query(CourseGapAnalysis)
        .filter(
            CourseGapAnalysis.user_id == user_id,
            CourseGapAnalysis.course_id == course.id,
        )
        .first()
    )
    if saved is None:
        return None
    payload = json.loads(saved.payload_json or "{}")
    payload["cached"] = True
    # SQLite stores DateTime without tzinfo — re-attach UTC so the timestamp
    # matches the freshly-computed responses exactly (``+00:00`` suffix).
    analyzed = saved.analyzed_at
    if analyzed is not None and analyzed.tzinfo is None:
        analyzed = analyzed.replace(tzinfo=timezone.utc)
    payload["analyzed_at"] = analyzed.isoformat() if analyzed else None
    if isinstance(payload.get("document_count"), int):
        payload["new_notes_since_analysis"] = max(
            0, course_document_count(db, user_id, course) - payload["document_count"]
        )
    return payload


def _save_gaps(db: Session, user_id: int, course_id: int, payload: dict[str, Any]) -> None:
    """Upsert the analysis payload for a user + course (one row).

    The stored ``analyzed_at`` is the payload's own timestamp, so a later GET
    that reloads the saved copy reports exactly the moment the analysis was
    actually computed.
    """
    row = (
        db.query(CourseGapAnalysis)
        .filter(
            CourseGapAnalysis.user_id == user_id,
            CourseGapAnalysis.course_id == course_id,
        )
        .first()
    )
    if row is None:
        row = CourseGapAnalysis(user_id=user_id, course_id=course_id)
        db.add(row)
    row.payload_json = json.dumps(payload, default=str)
    row.analyzed_at = datetime.fromisoformat(payload["analyzed_at"]) if payload.get("analyzed_at") else datetime.now(timezone.utc)
    db.commit()
    # Every analysis (first compute AND explicit re-analyze) is logged to the
    # history so the UI can show how this subject's gaps changed over time.
    record_gap_history(db, user_id, course_id=course_id, payload=payload)


def _invalidate_saved_gaps(db: Session, user_id: int, course_id: int) -> None:
    """Drop the cached analysis (used after a resync, since data changed)."""
    db.query(CourseGapAnalysis).filter(
        CourseGapAnalysis.user_id == user_id,
        CourseGapAnalysis.course_id == course_id,
    ).delete()
    db.commit()


@router.get("/{course_id}/gaps")
def course_gaps_endpoint(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Gap analysis for the subject, computed from its actual data.

    Results are saved per course: the first call computes and stores the
    analysis; later calls return the saved copy (``cached: True``) without
    recomputing. Recompute happens only on the explicit
    ``POST /{course_id}/gaps/analyze`` or after a resync.
    """
    course = _course_or_404(db, current_user.id, course_id)
    saved = _load_saved_gaps(db, current_user.id, course)
    if saved is not None:
        return saved
    payload = course_gaps(db, current_user.id, course)
    payload["cached"] = False
    payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    _save_gaps(db, current_user.id, course.id, payload)
    return payload


@router.post("/{course_id}/gaps/analyze")
def course_gaps_reanalyze(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Force a fresh Gap Analysis for the subject and save the result.

    The only path that recomputes without a resync — used by the UI's
    "Re-analyze" action so the user stays in control of when results update.
    """
    course = _course_or_404(db, current_user.id, course_id)
    payload = course_gaps(db, current_user.id, course)
    payload["cached"] = False
    payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    _save_gaps(db, current_user.id, course.id, payload)
    return payload


@router.get("/{course_id}/gaps/history")
def course_gaps_history(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Snapshot log of this subject's gap analyses (oldest → newest).

    Each entry is a compact diffable snapshot: counts, coverage, and the
    per-gap/per-strength summaries of that analysis. The frontend renders the
    timeline and compares consecutive snapshots (new gaps, resolved gaps,
    level improvements).
    """
    _course_or_404(db, current_user.id, course_id)
    return {"history": list_gap_history(db, current_user.id, course_id=course_id)}


@router.post("/{course_id}/resync")
def resync_course(
    course_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Resync the course with its data sources (Second Brain tags + Google
    Classroom) and return the refreshed content payload.

    Both syncs are idempotent (merge-by-google-id / one-course-per-tag), so
    re-running never duplicates records. The current subject's data is updated
    in place — no manual app refresh needed.
    """
    course = _course_or_404(db, current_user.id, course_id)

    kb = derive_courses_from_tags(db, current_user.id)

    # Data may have changed — a saved Gap Analysis would be stale. Drop it so
    # the next gaps request recomputes from the fresh data.
    _invalidate_saved_gaps(db, current_user.id, course_id)

    # A stale ``kb_tag`` course whose ``course:*`` tag no longer exists is
    # removed by the derivation — surface that instead of erroring.
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.id)
        .first()
    )
    if course is None:
        return {"kb": kb, "course_removed": True, "content": None}

    classroom = None
    if course.google_id or course.source_type == "classroom":
        try:
            courses_res = classroom_sync.sync_classroom_courses(db, current_user.id)
            assignments_res = classroom_sync.sync_classroom_assignments(db, current_user.id)
            classroom = {
                "courses": len(courses_res.get("courses", [])),
                "assignments": len(assignments_res.get("assignments", [])),
                "source": courses_res.get("source"),
                "warning": courses_res.get("warning"),
            }
        except Exception as exc:  # noqa: BLE001 — a Classroom failure must not block the KB part
            classroom = {"error": str(exc)}
        db.refresh(course)

    return {
        "kb": kb,
        "classroom": classroom,
        "content": course_content(db, current_user.id, course),
    }


@router.post("/sync-kb")
def sync_courses_from_kb(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Derive/refresh one Course per Second Brain ``course:*`` tag."""
    return derive_courses_from_tags(db, current_user.id)
