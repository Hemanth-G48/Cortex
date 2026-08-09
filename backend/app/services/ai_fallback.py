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
# Second Brain Phase 4 — note intelligence fallbacks (Ideas 31–40)
# ---------------------------------------------------------------------------

def demo_kb_summary(content: str | None = None) -> dict:
    """Deterministic structured summary fallback (Idea 31, phrase 8).

    TL;DR = first heading + first N chars; key points = heading list when
    available, else the longest early sentences; definitions/open questions
    are empty (never hallucinated).
    """
    content = (content or "").strip()
    headings = re.findall(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)
    sentences = [
        s.strip() for s in re.split(r"[.!?\n]+", content) if len(s.strip()) > 30
    ]
    tldr = ""
    if headings:
        tldr = f"About {headings[0].strip().lower()}."
    if sentences:
        lead = sentences[0][:240]
        tldr = f"{tldr} {lead}".strip() if tldr else lead
    if not tldr:
        tldr = (content[:200] + "…") if content else "No content to summarize."
    key_points = [f"{h.strip()}" for h in headings[:6]] if headings else sentences[:4]
    return {
        "summary": tldr,
        "key_points": key_points or ["No key points available."],
        "definitions": [],
        "open_questions": [],
    }


def demo_explain(concept: str, depth: str, definition: str | None, excerpt: str | None) -> dict:
    """Deterministic explanation fallback (Idea 32, phrase 17).

    Definition comes from the ``kb_concepts`` row when available; otherwise a
    short excerpt of the top matching chunk. No hallucination risk.
    """
    concept = concept or "this concept"
    depth = depth if depth in ("overview", "deep_dive", "eli5", "analogy", "derivation") else "overview"
    body = definition or excerpt or f"No note in your vault covers '{concept}' yet."
    if depth == "eli5":
        lead = body.split(".")[0][:140]
        explanation = f"{concept}: simply put, {lead.lower() if lead else body}."
    elif depth == "analogy":
        explanation = f"Think of {concept} as a building block: {body}"
    else:
        explanation = f"{concept} — {body}"
    return {
        "explanation": explanation[:2000],
        "citations": [],
    }


def demo_kb_flashcards(concepts: list[dict] | None = None) -> list[dict]:
    """Deterministic card candidates (Idea 34, phrase 37).

    ``concepts`` is a list of ``{"name", "definition"}`` — one ``What is X?``
    card per concept with a definition (or a placeholder) for the answer.
    """
    cards: list[dict] = []
    for c in concepts or []:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        answer = (c.get("definition") or "").strip()
        if not answer:
            answer = f"A key concept mentioned in your notes: {name}."
        cards.append(
            {
                "question": f"What is {name}?",
                "answer": answer,
                "source_chunk_id": 0,
            }
        )
    return cards[:8]


def demo_braindump_split(text: str) -> list[dict]:
    """Deterministic section proposals for a brain dump (Idea 40, phrase 95).

    Splits on blank lines / paragraph boundaries when the text is long; a single
    section otherwise. Char offsets are byte-accurate to the input string.
    """
    text = text or ""
    if len(text) < 400:
        return [{"title": "Notes", "char_start": 0}]
    paragraphs = re.split(r"\n\s*\n", text)
    sections: list[dict] = []
    offset = 0
    for para in paragraphs:
        title = re.sub(r"[#*_`]+", "", para.strip().split("\n")[0])[:60].strip()
        if not title:
            title = "Notes"
        sections.append({"title": title, "char_start": offset})
        offset += len(para) + 2
    return sections[:6]


def demo_quality_suggestions(content: str, link_count: int, has_outline: bool, concept_count: int) -> list[dict]:
    """Deterministic note-quality suggestions (Idea 39, phrase 85 fallback)."""
    suggestions: list[dict] = []
    content = content or ""
    if len(content) > 4000 and not has_outline:
        suggestions.append(
            {"action": "split", "detail": "This note is long and has no headings — consider splitting it into sections."}
        )
    elif len(content) < 200:
        suggestions.append(
            {"action": "expand", "detail": "This note is very short — expand it with the key ideas it should capture."}
        )
    if concept_count == 0:
        suggestions.append(
            {"action": "tag", "detail": "No concepts were detected — add a few inline tags or a frontmatter tags list."}
        )
    if link_count == 0:
        suggestions.append(
            {"action": "link", "detail": "This note links to nothing — connect it to related notes or concepts to make it discoverable."}
        )
    return suggestions[:5]


# ---------------------------------------------------------------------------
# Phase 5 — Subject Management Core fallbacks (Ideas 41–50)
# ---------------------------------------------------------------------------

_UNIT_HEADING_RE = re.compile(
    r"^\s*(?:unit|module|week|chapter|part)\s*[0-9IVX]+[.:)\u2013-]*\s+(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
_TOPIC_LINE_RE = re.compile(r"^\s*(?:\d{1,2}[.)-]|[-*u2022]|\u2022)\s+(.+)$")


def demo_syllabus_parse(text: str | None = None, filename: str | None = None) -> dict:
    """Deterministic syllabus parser fallback (Idea 42, phrase 15).

    Title from the first heading / filename; units from ``Unit/Module/Week``
    headings; topics from numbered/bullet lines inside each unit. Outcome
    sentences ("will be able to"/"outcomes") attach to the enclosing unit.
    """
    text = (text or "").strip()
    lines = text.splitlines()

    title = None
    for line in lines:
        m = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if m:
            title = m.group(1).strip()
            break
    if not title and filename:
        title = re.sub(r"\.[A-Za-z0-9]+$", "", filename)
    if not title:
        title = "Course Syllabus"

    units: list[dict] = []
    current_unit: dict | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Markdown headings ("## Unit 1: …") — match on the text after the #s.
        match_line = re.sub(r"^#{1,6}\s+", "", line)
        m = _UNIT_HEADING_RE.match(match_line)
        if m:
            current_unit = {
                "title": m.group(1).strip(),
                "description": None,
                "topics": [],
                "deadlines": [],
            }
            units.append(current_unit)
            continue
        if current_unit is None:
            continue
        tm = _TOPIC_LINE_RE.match(match_line)
        if tm:
            topic = tm.group(1).strip()
            if len(topic) > 2 and not re.match(r"^(due|deadline|exam|midterm|final|assignment)", topic, re.I):
                current_unit["topics"].append({"name": topic, "outcomes": []})
        if re.match(r"^(due|deadline|exam|midterm|final)\b", line, re.I) and len(line) < 160:
            current_unit["deadlines"].append(line)

    # Outcome sentences: "Upon completion ... will be able to ..."
    outcomes: list[str] = []
    for raw in lines:
        low = raw.lower()
        if ("will be able to" in low or "upon completion" in low or "learning outcomes" in low) and len(raw.strip()) > 25:
            outcomes.append(re.sub(r"^[#*\-\s]+\|?\s*", "", raw.strip()))
    if outcomes:
        unit = units[0] if units else None
        target = unit["topics"][0] if unit and unit["topics"] else None
        if target:
            target["outcomes"] = outcomes[:5]

    return {
        "title": title,
        "semester": None,
        "credits": None,
        "grading": None,
        "units": units[:100],
    }


def demo_topic_deps(units: list[dict]) -> list[dict]:
    """Deterministic dependency seed fallback (Idea 46, phrase 52).

    Later topics depend on the immediately preceding topic within the same
    unit (syllabus order is the safest no-LLM heuristic).
    """
    deps: list[dict] = []
    for unit in units or []:
        topics = [t.get("name") for t in (unit.get("topics") or []) if t.get("name")]
        for i in range(1, len(topics)):
            deps.append({"topic_a": topics[i], "depends_on": [topics[i - 1]]})
    return deps


_DIFFICULTY_HARD = ("proof", "theorem", "derivation", "optimization", "analysis", "complexity", "theory", "topology", "algorithm")
_DIFFICULTY_EASY = ("introduction", "overview", "basics", "definition", "recall", "history")


def demo_difficulty(name: str, description: str | None = None, outcomes: list[str] | None = None) -> dict:
    """Deterministic difficulty fallback (Idea 48, phrase 76)."""
    haystack = f"{name} {description or ''} {' '.join(outcomes or [])}".lower()
    if any(k in haystack for k in _DIFFICULTY_HARD):
        return {"difficulty": "H", "confidence": 0.7}
    if any(k in haystack for k in _DIFFICULTY_EASY):
        return {"difficulty": "E", "confidence": 0.7}
    return {"difficulty": "M", "confidence": 0.5}


def demo_outcome_expand(topic: str, raw: list[str]) -> list[str]:
    """Deterministic outcome expansion fallback (Idea 50, phrase 94)."""
    clean = [r.strip() for r in (raw or []) if r.strip()]
    if len(clean) >= 2:
        return clean[:5]
    return [
        f"Explain the core ideas of {topic}.",
        f"Apply {topic} to a worked example.",
        f"Connect {topic} to related course concepts.",
    ][:5]


# ---------------------------------------------------------------------------
# Phase 6 — Study Planning & Execution fallbacks (Ideas 51–60)
# ---------------------------------------------------------------------------

def demo_study_plan_grounded(topic_names: list[str], weeks: int = 6) -> list[dict]:
    """Deterministic topic-grounded weeks fallback (Idea 51, phrase 6).

    Equal weekly split of the topic list; every topic appears exactly once.
    """
    names = [n for n in (topic_names or []) if n]
    weeks = max(1, weeks)
    out: list[dict] = []
    if not names:
        return out
    chunk = max(1, -(-len(names) // weeks))
    for i in range(0, len(names), chunk):
        bucket = names[i : i + chunk]
        out.append(
            {
                "week": len(out) + 1,
                "topic": ", ".join(bucket),
                "topic_ids": [],
                "hours_estimate": round(max(1.0, len(bucket) * 1.5), 1),
                "tasks": [f"Study {n}" for n in bucket],
            }
        )
    return out


def demo_assignment_subtasks(title: str, hours_total: float) -> list[dict]:
    """Deterministic subtask fallback (Idea 54, phrase 36): equal split."""
    total = max(1.0, float(hours_total or 3.0))
    steps = ["Read the prompt and requirements", "Research and outline", "Draft and revise"]
    per = round(total / len(steps), 1)
    return [{"title": f"{title}: {s}", "hours": per} for s in steps]


# ---------------------------------------------------------------------------
# Phase 7 — AI Tutor & Assessment fallbacks (Ideas 61–70)
# ---------------------------------------------------------------------------

def demo_practice_questions(topic: str, count: int = 5, difficulty: str = "M") -> list[dict]:
    """Deterministic question-bank fallback (Idea 63, phrase 27).

    Template MCQs per Bloom level built from the topic name — options are
    stable placeholders so the shape matches the LLM schema exactly.
    """
    count = max(1, min(10, count))
    blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    out: list[dict] = []
    for i in range(count):
        bloom = blooms[i % len(blooms)]
        question = f"({bloom}) Which statement best describes a key idea of {topic}?"
        out.append(
            {
                "question": question,
                "options": [
                    f"The core definition of {topic}",
                    "A detail unrelated to the topic",
                    "A common misconception",
                    "None of the above",
                ],
                "answer": f"The core definition of {topic}",
                "explanation": f"This captures the central idea of {topic}.",
                "bloom_level": bloom,
                "difficulty": difficulty[:1] or "M",
            }
        )
    return out


def demo_grade_advanced(question: str, expected: str, answer: str) -> dict:
    """Deterministic advanced-grading fallback (Idea 66, phrase 56).

    Partial credit from keyword overlap against the expected answer; canned
    strengths/next-steps so the structured shape matches the LLM schema.
    """
    def _words(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9']+", (text or "").lower()))

    exp = _words(expected)
    ans = _words(answer)
    if not exp:
        score, overlap = 0, 0.0
    else:
        overlap = len(exp & ans) / len(exp)
        score = max(0, min(100, round(overlap * 100)))
    if score >= 90:
        strengths = ["Your answer covers the core points."]
        misconceptions: list[str] = []
    else:
        strengths = ["You made a good attempt with relevant ideas."]
        misconceptions = ["Some key points from the expected answer are missing."]
    action_items = ["Review the expected answer and fill the missing key points."]
    if score < 50:
        action_items.insert(0, "Re-read the note covering this topic.")
    return {
        "score": score,
        "strengths": strengths,
        "misconceptions": misconceptions,
        "action_items": action_items,
    }


def demo_mistake_analysis(question: str, model_solution: str, student_answer: str) -> dict:
    """Deterministic mistake-walkthrough fallback (Idea 68, phrase 77)."""
    def _words(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9']+", (text or "").lower()))

    missing = sorted(_words(model_solution) - _words(student_answer))
    points = [f"Did not mention: {w}" for w in missing[:4]] or ["Answer diverged from the model solution"]
    return {
        "divergence": "Your answer missed key points of the model solution.",
        "missed_points": points,
        "recommendation": "Re-read the note that explains this topic and compare with the model solution.",
    }


def demo_skill_mapping(topics: list[str]) -> list[dict]:
    """Deterministic topic→skill fallback (Idea 70, phrase 94).

    Keyword match against the seeded taxonomy; topics with no hits are skipped.
    """
    try:
        from app.services.kb.skills import _keyword_match
    except Exception:  # noqa: BLE001
        return []
    out: list[dict] = []
    for t in (topics or []):
        matches = _keyword_match(t)
        if matches:
            out.append({"topic": t, "skill_id": matches[0]})
    return out


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
