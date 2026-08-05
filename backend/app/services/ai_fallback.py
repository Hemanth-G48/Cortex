"""Deterministic AI fallback generators.

Every AI feature falls back to these local generators when the provider is
unreachable/disabled — mirroring Shiori-v1's demo-payload fallback so the app
remains fully functional offline (``AI_ENABLED=false`` keeps tests hermetic).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

_DEMO_QUIZ = [
    {
        "q": "What is photosynthesis?",
        "opts": ["Making food from sunlight", "Breaking down glucose", "Cell division", "DNA replication"],
        "ans": 0,
    },
    {
        "q": "What is the powerhouse of the cell?",
        "opts": ["Nucleus", "Ribosome", "Mitochondria", "Golgi apparatus"],
        "ans": 2,
    },
    {
        "q": "What does DNA stand for?",
        "opts": ["Deoxyribonucleic Acid", "Dynamic Nucleic Acid", "Digital Nucleotide Array", "Dextro Nucleic Acid"],
        "ans": 0,
    },
]


def demo_quiz(content: str | None = None) -> list[dict]:
    """Deterministic 3-question MCQ quiz. Port of Shiori's ``DEMO_QUIZ``.

    When content is provided the first question is re-worded around a sentence
    from the content so the fallback still feels content-aware.
    """
    quiz = [dict(q) for q in _DEMO_QUIZ]
    if content:
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", content or "") if len(s.strip()) > 20]
        if sentences:
            topic = sentences[0][:80]
            quiz[0]["q"] = f'True or best choice about: "{topic}"?'
            quiz[0]["opts"] = ["This statement is correct", "This statement is false", "Not enough information", "None of the above"]
            quiz[0]["ans"] = 0
    return quiz


# ---------------------------------------------------------------------------
# Study plans
# ---------------------------------------------------------------------------

_DEMO_WEEKS = [
    {"week": 1, "topic": "Cell Biology & Organelles", "tasks": ["Read Ch 1-2", "Make flashcards", "Practice diagrams"]},
    {"week": 2, "topic": "Genetics & DNA", "tasks": ["Read Ch 3-4", "Punnett square practice", "Review lecture notes"]},
    {"week": 3, "topic": "Evolution & Ecology", "tasks": ["Read Ch 5-6", "Watch videos", "Past exam questions"]},
    {"week": 4, "topic": "Review & Practice Exams", "tasks": ["Full practice test", "Review weak areas", "Final revision"]},
]


def demo_study_plan(subject: str, exam_date: str | None = None) -> dict:
    """Deterministic 4-week plan. Port of Shiori's ``DEMO_PLAN``."""
    return {
        "subject": subject or "Study Plan",
        "exam_date": exam_date,
        "weeks": [dict(w) for w in _DEMO_WEEKS],
    }


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------

_DIFFICULTY_TEMPLATES = {
    "easy": [
        {"front": "What is the most basic definition of the topic?", "back": "The fundamental, surface-level definition a beginner should recall."},
        {"front": "Name one key term associated with this topic.", "back": "The most frequently cited keyword in the study material."},
    ],
    "basic": [
        {"front": "What are the core concepts of this topic?", "back": "The main ideas that everything else builds on."},
        {"front": "Give a simple example of the topic in action.", "back": "A short, concrete illustration drawn from the material."},
    ],
    "medium": [
        {"front": "Explain how the key concepts connect.", "back": "A synthesis of the relationships between the main ideas in the material."},
        {"front": "What is a common misconception here?", "back": "A frequent error students make when applying this concept."},
    ],
    "hard": [
        {"front": "Solve a multi-step problem involving this topic.", "back": "A worked outline of the reasoning required to combine the concepts."},
        {"front": "Compare this concept with a related one.", "back": "A structured contrast of similarities and differences."},
    ],
    "olympic": [
        {"front": "Prove or derive the central result of this topic.", "back": "A rigorous derivation suitable for competition-level practice."},
        {"front": "Construct an edge case that breaks naive reasoning here.", "back": "A subtle counterexample demonstrating depth of understanding."},
    ],
}


def demo_flashcards(topic: str | None = None, difficulty: str = "basic") -> dict:
    """Deterministic card set. Port of Shiori's 5-difficulty prompt map."""
    cards = [dict(c) for c in _DIFFICULTY_TEMPLATES.get(difficulty, _DIFFICULTY_TEMPLATES["basic"])]
    if topic:
        for c in cards:
            c["front"] = c["front"].replace("this topic", f'"{topic}"')
            c["back"] = c["back"].replace("the material", f'"{topic}"')
    return {"cards": cards}


# ---------------------------------------------------------------------------
# Syllabus extraction
# ---------------------------------------------------------------------------

_DEMO_EXTRACTED = [
    {"title": "Essay 1: Personal Narrative", "due_date": "2026-02-14", "course": "English 101", "priority": "high"},
    {"title": "Midterm Exam", "due_date": "2026-03-10", "course": "English 101", "priority": "high"},
    {"title": "Research Paper Draft", "due_date": "2026-03-28", "course": "English 101", "priority": "medium"},
    {"title": "Final Presentation", "due_date": "2026-04-25", "course": "English 101", "priority": "high"},
]


def demo_syllabus(text: str | None = None) -> list[dict]:
    """Deterministic extraction. Port of Shiori's ``DEMO_EXTRACTED``."""
    items = [dict(a) for a in _DEMO_EXTRACTED]
    if text:
        # Pull a plausible course name from the pasted syllabus when possible.
        m = re.search(r"\b([A-Z][a-zA-Z& ]{2,40}?\b(?:Course|101|102|201|202|301|302|MATH|CS|ENG|HIST|PHYS|BIO|CHEM)\b)", text)
        if m:
            course = m.group(1).strip()
            for item in items:
                item["course"] = course
    return items


# ---------------------------------------------------------------------------
# Written-answer grading
# ---------------------------------------------------------------------------

def demo_grade_answer(question: str, expected: str, answer: str) -> dict:
    """Deterministic grading fallback — case/whitespace-insensitive exact match."""
    norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().lower())
    correct = norm(answer) == norm(expected)
    if correct:
        explanation = "Correct — your answer matches the expected answer."
    else:
        explanation = f"Not quite. The expected answer was: {expected}"
    return {"correct": correct, "explanation": explanation}


# ---------------------------------------------------------------------------
# AI chat — local heuristic fallback (port of Shiori's getLocalResponse)
# ---------------------------------------------------------------------------

def local_chat_response(message: str, context: dict | None = None) -> dict:
    """Rule-based chat assistant response built from real DB context.

    Port of Shiori-v1's ``getLocalResponse`` heuristics (assignment/study/
    grade/deadline/hello/help branches). ``context`` may include:
    ``assignments`` (list with due_date, course_id, status), ``courses``
    (list with title, id), ``pomodoro`` stats, ``user`` XP/level.
    """
    context = context or {}
    assignments = context.get("assignments") or []
    courses = context.get("courses") or []
    user = context.get("user") or {}

    today = date.today()
    pending = [a for a in assignments if a.get("status") != "Completed"]
    upcoming = sorted(
        [a for a in pending if a.get("due_date")],
        key=lambda a: a["due_date"],
    )[:5]
    course_titles = [c.get("title") for c in courses if c.get("title")]
    subjects = ", ".join(course_titles[:5]) or "your courses"

    def _deadline_lines(items, fmt: str = "short") -> str:
        lines = []
        for a in items:
            try:
                d = date.fromisoformat(str(a["due_date"]))
                label = d.strftime("%b %d") if fmt == "short" else d.strftime("%B %d")
            except ValueError:
                label = str(a["due_date"])
            lines.append(f"• {a.get('title', 'Untitled')} — {label}")
        return "\n".join(lines)

    lower = (message or "").lower()

    if any(k in lower for k in ("assignment", "homework", "due", "deadline")):
        if upcoming:
            return {"message": f"You have {len(pending)} pending assignments. Upcoming deadlines:\n{_deadline_lines(upcoming)}\n\nWant me to generate a study plan around these?"}
        return {"message": "No pending assignments — great work staying ahead! Ask about study plans or grades anytime."}

    if any(k in lower for k in ("study", "plan", "schedule")):
        if pending:
            return {"message": f"I can build a personalized study plan for your {len(pending)} pending assignments across {subjects}. Head to Study Plans and hit Generate!"}
        return {"message": "No pending assignments right now. Add tasks or tell me the subject and I'll help you plan."}

    if any(k in lower for k in ("grade", "gpa", "score")):
        return {"message": "Open the Grades page to track your weighted course grades, cumulative GPA, and what you need on finals. Add each graded assignment for an accurate picture."}

    if any(k in lower for k in ("hello", "hi ", "hey", "morning", "good morning")):
        status = f"You have {len(pending)} tasks pending." if pending else "You're all caught up!"
        return {"message": f"Hey! I'm Shiori, your AI study companion. {status} How can I help you today?"}

    if "help" in lower or "?" in message.strip()[-1:]:
        return {"message": f"I can help with:\n• Analyzing your {len(assignments)} assignments across {subjects}\n• Creating personalized study plans\n• Tracking grades and GPA\n• Managing deadlines\n\nJust ask — or try the Study Plans, Quiz, and Flashcards pages!"}

    if "xp" in lower or "level" in lower:
        lvl = user.get("current_level", "—")
        xp = user.get("total_xp", 0)
        return {"message": f"You're at level {lvl} with {xp} total XP. Keep completing tasks and habits to earn more!"}

    return {"message": "I'm here to help you study smarter! I can analyze assignments, create study plans, track grades, and manage deadlines. What would you like to work on?"}
