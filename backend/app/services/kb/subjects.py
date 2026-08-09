"""Phase 5 subject service (Ideas 41, 43).

Review-before-write is the rule: ``propose`` stores only a ``SubjectProfile``
row; ``confirm`` is the single place that writes the existing
``curriculum_subjects`` / ``curriculum_units`` tables. Semester detection
(keywords + date cross-check + current-term default) lives here.
"""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    CurriculumCourse,
    CurriculumSubject,
    CurriculumUnit,
    SubjectProfile,
    User,
)
from app.services.kb import KbService, utcnow
from app.services.kb.syllabus import parse_syllabus

PROPOSED, CONFIRMED, REJECTED = "proposed", "confirmed", "rejected"

# "Fall 2026" / "2026 Spring …" / "Semester 2, 2026" / "CS101_Fall_2026.pdf" …
# Lookarounds (not \b) so underscores/digits between term and year still match.
_SEMESTER_RE = re.compile(
    r"(?i)(?<![a-z])(spring|summer|fall|autumn|winter|semester|term|trimester)(?![a-z])"
    r"[^a-z\n]{0,40}?(?<![0-9])(19|20)\d{2}(?![0-9])"
    r"|(?<![0-9])(19|20)\d{2}(?![0-9])[^a-z\n]{0,40}?(?<![a-z])(spring|summer|fall|autumn|winter|semester|term|trimester)(?![a-z])"
)
_YEAR_ONLY_RE = re.compile(r"\b(19|20)\d{2}\b")
_TERM_NAME = {"spring", "summer", "fall", "autumn", "winter"}


def current_term(today: date | None = None) -> str:
    """Default term from the server date (phrase 24)."""
    today = today or date.today()
    month = today.month
    if month in (1, 2, 3, 4):
        season = "Spring"
    elif month in (5, 6, 7):
        season = "Summer"
    elif month in (8, 9, 10, 11):
        season = "Fall"
    else:
        season = "Winter"
    return f"{season} {today.year}"


def _clean_term(text: str | None) -> str | None:
    """Normalise a detected term to 'Fall 2026' form."""
    if not text:
        return None
    # Underscores ("CS101_Fall_2026") would break \b boundaries — space them out.
    text = " ".join(re.sub(r"[^a-z0-9 ]", " ", text, flags=re.I).split())
    m = re.search(r"(?i)\b(spring|summer|fall|autumn|winter)\b", text)
    y = re.search(r"\b(19|20)\d{2}\b", text)
    season = {"autumn": "Fall"}.get((m.group(1).lower() if m else ""), (m.group(1).title() if m else ""))
    if season and y:
        return f"{season} {y.group(0)}"
    if m and not y:
        return m.group(1).title()
    if y:
        # year alone → match to the closest term around the current date
        return current_term()
    return None


def detect_semester(text: str | None, filename: str | None = None) -> str | None:
    """Keyword scan over syllabus text + filename (phrase 22)."""
    for source in (text or "", filename or ""):
        m = _SEMESTER_RE.search(source)
        if m:
            cleaned = _clean_term(m.group(0))
            if cleaned:
                return cleaned
    return None


def semester_from_deadlines(deadlines: list[str]) -> str | None:
    """Cross-check deadlines for a term hint (phrase 23)."""
    for d in deadlines or []:
        m = _SEMESTER_RE.search(d)
        if m:
            cleaned = _clean_term(m.group(0))
            if cleaned:
                return cleaned
    return None


def propose(db: Session, user_id: int, text: str | None, filename: str | None = None) -> dict:
    """Parse a syllabus and create a *proposed* profile (phrases 4–5)."""
    parsed = parse_syllabus(text, filename, db=db, user_id=user_id)
    data = parsed["parsed"]
    # The LLM's structured ``semester`` wins when it looks like a term
    # ("Fall 2026"/"Spring 2027"), then keyword/deadline detection, then the
    # current-term default.
    parsed_semester = (data.get("semester") or "").strip()
    semester = parsed_semester if detect_semester(parsed_semester) else None
    if not semester:
        semester = detect_semester(text, filename)
    if not semester:
        semester = semester_from_deadlines(
            [d for u in data.get("units", []) for d in u.get("deadlines", [])]
        )
    if not semester:
        semester = current_term()

    profile = SubjectProfile(
        user_id=user_id,
        raw_syllabus_text=(text or "")[:200_000],
        parsed_json=KbService.json_dumps(data),
        semester=semester,
        status=PROPOSED,
    )
    db.add(profile)
    db.flush()
    return {"profile": profile, "fallback": parsed["fallback"]}


def get_profile(db: Session, user_id: int, profile_id: int) -> SubjectProfile | None:
    return (
        db.query(SubjectProfile)
        .filter(SubjectProfile.id == profile_id, SubjectProfile.user_id == user_id)
        .first()
    )


def list_profiles(db: Session, user_id: int, status: str | None = None) -> list[SubjectProfile]:
    q = db.query(SubjectProfile).filter(SubjectProfile.user_id == user_id)
    if status:
        q = q.filter(SubjectProfile.status == status)
    return q.order_by(SubjectProfile.created_at.desc()).all()


def _user_program(db: Session, user_id: int) -> CurriculumCourse | None:
    """The user's enrolled program (SyllabusAI enrollment), else first program."""
    user = db.query(User).get(user_id)
    if user and user.program_id:
        program = db.query(CurriculumCourse).get(user.program_id)
        if program:
            return program
    return db.query(CurriculumCourse).order_by(CurriculumCourse.id.asc()).first()


def _derive_code(name: str, subject_id: int) -> str:
    words = re.findall(r"[A-Za-z]+", name or "")
    if not words:
        return f"SUBJ{subject_id}"
    base = "".join(w[0] for w in words[:3]).upper() or name[:4].upper()
    return f"{base}{subject_id}"


def confirm(
    db: Session,
    user_id: int,
    profile: SubjectProfile,
    *,
    program_id: int | None = None,
    name: str | None = None,
    code: str | None = None,
    credits: int | None = None,
) -> SubjectProfile:
    """Write curriculum rows + link the profile (phrase 7)."""
    if profile.status != PROPOSED:
        raise ValueError("Only proposed profiles can be confirmed")

    parsed = KbService.json_loads(profile.parsed_json) or {}
    subject_name = name or parsed.get("title") or "Untitled Subject"
    subject_code = code or _derive_code(subject_name, profile.id)
    subject_credits = credits if credits is not None else parsed.get("credits")

    if program_id:
        program = db.query(CurriculumCourse).get(program_id)
        if program is None:
            raise ValueError("Program not found")
    else:
        program = _user_program(db, user_id)
    if program is None:
        raise ValueError("No program found — create one in the curriculum admin first")

    subject = CurriculumSubject(
        program_id=program.id,
        name=subject_name[:200],
        code=subject_code[:50],
        semester=None,  # string term lives on profile + units (Idea 43)
        credits=subject_credits or 3,
        description=parsed.get("grading"),
        is_active=True,
    )
    db.add(subject)
    db.flush()

    for i, unit in enumerate(parsed.get("units", []), start=1):
        unit_row = CurriculumUnit(
            subject_id=subject.id,
            unit_number=i,
            name=(unit.get("title") or f"Unit {i}")[:200],
            description=unit.get("description"),
            is_active=True,
            semester=profile.semester,
        )
        db.add(unit_row)

    profile.curriculum_subject_id = subject.id
    profile.status = CONFIRMED
    profile.updated_at = utcnow()
    return profile


def reject(db: Session, user_id: int, profile: SubjectProfile) -> SubjectProfile:
    profile.status = REJECTED
    profile.updated_at = utcnow()
    return profile
