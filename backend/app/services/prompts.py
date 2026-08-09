"""Prompt templates for AI-generated summaries and quizzes."""
from __future__ import annotations


# Phase 4 explanation depths (Idea 32) and their prompt variants.
EXPLAIN_DEPTHS = ("overview", "deep_dive", "eli5", "analogy", "derivation")


def summary_prompt(content: str) -> str:
    """Prompt for a single-unit summary. Returns strict JSON only."""
    snippet = content[:15000]
    return (
        "Summarize the following educational content. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with exactly "
        "two keys: \"summary\" (a concise paragraph) and \"key_points\" "
        "(an array of 3-6 short bullet strings).\n\n"
        f"Content:\n{snippet}"
    )


def multi_unit_summary_prompt(units: list[tuple[str, str]]) -> str:
    """Prompt for a multi-unit summary. Returns strict JSON only."""
    parts = []
    for name, content in units:
        snippet = content[:15000]
        parts.append(f"## Unit: {name}\n\n{snippet}")
    combined = "\n\n".join(parts)
    return (
        "Summarize the following educational units. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with three keys: "
        "\"summary\" (a concise paragraph covering all units), \"key_points\" "
        "(an array of 3-6 short bullet strings), and \"sections\" (an array of "
        "objects, each with \"unit\" (the unit name) and \"summary\" (a short "
        "paragraph for that unit)).\n\n"
        f"Units:\n{combined}"
    )


def quiz_prompt(content: str, num_questions: int, difficulty: str) -> str:
    """Prompt for quiz generation. Returns strict JSON only."""
    snippet = content[:15000]
    return (
        f"Generate exactly {num_questions} multiple-choice questions from the "
        f"following content at {difficulty} difficulty. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with one key "
        "\"questions\" which is an array of objects. Each object must have: "
        "\"question\" (string), \"options\" (array of exactly 4 strings), "
        "\"correct_index\" (integer 0-3), and \"explanation\" (string).\n\n"
        f"Content:\n{snippet}"
    )


# ---------------------------------------------------------------------------
# Phase 4 — Note Intelligence & Content Generation (Ideas 31–40)
# ---------------------------------------------------------------------------

def kb_summary_prompt(content: str) -> str:
    """Prompt for a structured document summary (Idea 31, phrase 5).

    Returns strict JSON with four keys: ``summary`` (TL;DR), ``key_points``
    (array), ``definitions`` (array of {term, definition}), and
    ``open_questions`` (array of strings).
    """
    snippet = content[:18000]
    return (
        "Summarize the following document. Return STRICT JSON only, no markdown, "
        "no extra text. The JSON must be an object with exactly four keys: "
        "\"summary\" (a concise TL;DR paragraph), \"key_points\" (an array of "
        "3-6 short bullet strings), \"definitions\" (an array of objects with "
        "\"term\" and \"definition\" for key terms introduced in the document; "
        "empty array if none), and \"open_questions\" (an array of 0-3 questions "
        "the document leaves unanswered).\n\n"
        f"Document:\n{snippet}"
    )


def explain_prompt(
    concept: str,
    depth: str,
    context: str,
    doc_titles: list[tuple[int, str]],
) -> str:
    """Prompt for a grounded explanation at one of five depths (Idea 32).

    The context is a numbered list of retrieved chunks (``[n] ...``); the model
    MUST cite the chunks it uses as ``citations`` (array of chunk-index numbers)
    so every claim is traceable to the user's own vault.
    """
    depth = depth if depth in EXPLAIN_DEPTHS else "overview"
    depth_guidance = {
        "overview": "a concise high-level overview",
        "deep_dive": "a thorough technical deep-dive",
        "eli5": "a simple explanation a child could understand (plain words, short sentences)",
        "analogy": "an intuitive explanation built around clear analogies",
        "derivation": "a step-by-step derivation that shows the reasoning chain",
    }[depth]
    titles = "; ".join(f"[{i}] {t}" for i, t in doc_titles) or "(vault notes)"
    return (
        f"Explain \"{concept}\" as {depth_guidance}. Ground your answer ONLY in "
        "the numbered excerpts below from the user's own notes. Return STRICT JSON "
        "only with two keys: \"explanation\" (the answer text; use [n] markers inline "
        "to cite excerpts) and \"citations\" (an array of the excerpt numbers you "
        "used, e.g. [1, 3]). Never invent facts that are not in the excerpts; if an "
        "excerpt does not cover the concept, say so in the explanation and return an "
        "empty citations array.\n\n"
        f"Available sources: {titles}\n\n"
        f"Excerpts:\n{context}"
    )


def kb_flashcards_prompt(chunks: str) -> str:
    """Prompt for candidate Q/A pairs from concept-rich chunks (Idea 34)."""
    return (
        "Create up to 8 flashcard candidates from the following notes. Return "
        "STRICT JSON only, no markdown. The JSON must be an object with one key "
        "\"cards\" — an array of objects each with \"question\" (short, concrete), "
        "\"answer\" (one or two sentences), and \"source_chunk_id\" (integer; use "
        "the chunk number the card is derived from, or 0 if unknown). Focus on "
        "facts a student must recall — definitions, formulas, mechanisms — not "
        "trivia.\n\n"
        f"Notes (chunk-id: text):\n{chunks}"
    )


def braindump_split_prompt(text: str) -> str:
    """Prompt for section proposals when filing a long brain dump (Idea 40)."""
    return (
        "The following is a raw brain-dump of notes. Propose logical sections to "
        "organize it. Return STRICT JSON only, no markdown, with one key "
        "\"sections\" — an array of objects each with \"title\" (short heading) and "
        "\"char_start\" (character offset in the text where the section begins). "
        "Return 2-6 sections that cover the whole text.\n\n"
        f"Text:\n{text[:20000]}"
    )


def quality_suggestions_prompt(content: str, concepts: list[str]) -> str:
    """Prompt for actionable note-improvement suggestions (Idea 39, phrase 85)."""
    concept_line = ", ".join(concepts) if concepts else "none detected"
    return (
        "Act as a note-quality coach. Based on the note text below, propose 2-5 "
        "concrete improvements a student could make. Return STRICT JSON only — an "
        "object with one key \"suggestions\" — an array of objects each with "
        "\"action\" (one of: split, define, link, expand, tag) and \"detail\" "
        "(one sentence describing the specific improvement).\n\n"
        f"Known concepts in the vault: {concept_line}\n\n"
        f"Note text:\n{content[:12000]}"
    )


# ---------------------------------------------------------------------------
# Phase 5 — Subject Management Core (Ideas 41–50)
# ---------------------------------------------------------------------------

def syllabus_parse_prompt(chunk: str) -> str:
    """Prompt for deep syllabus parsing (Idea 42, phrase 12).

    Strict schema: ``{title, semester, credits, grading, units: [{title,
    description, topics: [{name, outcomes}], deadlines}]}``. The caller merges
    per-chunk parses (phrase 14).
    """
    return (
        "Parse the following syllabus text. Return STRICT JSON only, no markdown, "
        "no extra text. The JSON must be an object with these keys: \"title\" "
        "(course name), \"semester\" (e.g. \"Fall 2026\" or null), \"credits\" "
        "(integer or null), \"grading\" (short description of grading scheme or "
        "null), and \"units\" (an array of objects, each with \"title\", "
        "\"description\" (or null), \"topics\" (array of objects with \"name\" "
        "and \"outcomes\" — an array of learning-outcome strings, may be empty), "
        "and \"deadlines\" (array of strings like \"Midterm — Mar 10\", may be "
        "empty)). Extract every unit and topic you can; never invent content. If "
        "a section of the text has no units, return an empty units array.\n\n"
        f"Syllabus:\n{chunk}"
    )


def topic_deps_prompt(units: list[dict]) -> str:
    """Prompt for seeding topic prerequisites (Idea 46, phrase 52).

    Asks for ``{dependencies: [{topic_a, depends_on: [topic_b, ...]}]}`` where
    topic names match the provided unit/topic list.
    """
    listing = "\n".join(
        f"- Unit {i + 1} ({u.get('title', '')}): "
        + ", ".join(t.get("name", "") for t in u.get("topics", []) or [])
        for i, u in enumerate(units)
    )
    return (
        "Given a course's units and topics, infer prerequisite relationships "
        "between topics (which topics a student must understand BEFORE others). "
        "Return STRICT JSON only — an object with one key \"dependencies\" — an "
        "array of objects each with \"topic_a\" (exact topic name from the list) "
        "and \"depends_on\" (array of exact topic names that are prerequisites of "
        "topic_a). Use exact names only; skip topics with no dependencies.\n\n"
        f"Course topics:\n{listing}"
    )


def topic_difficulty_prompt(name: str, description: str | None, outcomes: list[str]) -> str:
    """Prompt for rubric-based difficulty estimation (Idea 48, phrase 72)."""
    outcome_line = "; ".join(outcomes or []) or "none listed"
    return (
        "Estimate the learning difficulty of one topic for an undergraduate "
        "student. Return STRICT JSON only — an object with two keys: "
        "\"difficulty\" (exactly one of \"E\", \"M\", \"H\") and "
        "\"confidence\" (0.0-1.0). Consider the topic name, description, and "
        "learning outcomes: topics that require proving results, mathematical "
        "derivation, or abstract theory tend to be H; recall-level topics tend "
        "to be E.\n\n"
        f"Topic: {name}\nDescription: {description or 'none'}\nOutcomes: {outcome_line}"
    )


def outcomes_expand_prompt(topic: str, raw: list[str]) -> str:
    """Prompt to convert syllabus outcome phrases into measurable outcomes
    (Idea 50, phrase 93).
    """
    raw_line = "\n".join(f"- {r}" for r in raw) or "(none — derive sensible ones from the topic)"
    return (
        "Convert the following raw syllabus outcome statements into measurable, "
        "verifiable learning outcomes for a student. Each outcome should start "
        "with an action verb (e.g. 'derive', 'solve', 'explain', 'compare'). "
        "Return STRICT JSON only — an object with one key \"outcomes\" — an "
        "array of strings, 2-5 outcomes.\n\n"
        f"Topic: {topic}\nRaw outcomes:\n{raw_line}"
    )


# ---------------------------------------------------------------------------
# Phase 6 — Study Planning & Execution (Ideas 51–60)
# ---------------------------------------------------------------------------

def study_plan_prompt(
    subject: str,
    topic_names: list[str],
    hours_per_day: float,
    weeks: int,
) -> str:
    """Prompt for a topic-grounded weekly study plan (Idea 51, phrase 4)."""
    listing = "\n".join(f"- {t}" for t in topic_names) or "(no topics parsed)"
    return (
        f"Create a {weeks}-week study plan for \"{subject}\" with about "
        f"{hours_per_day} hours of study per day. Assign the topics below to "
        "weeks in a sensible learning order (foundations first). Return STRICT "
        "JSON only — an object with one key \"weeks\" — an array of objects "
        "each with \"week\" (integer), \"topic\" (short label), "
        "\"topic_ids\" (leave empty array), \"hours_estimate\" (number), and "
        "\"tasks\" (array of 2-4 concrete task strings). Cover every topic at "
        "least once; never invent topics outside the list.\n\n"
        f"Topics:\n{listing}"
    )


def assignment_plan_prompt(title: str, description: str | None, due_date: str) -> str:
    """Prompt for an assignment subtask breakdown (Idea 54, phrase 31)."""
    return (
        f"Break this assignment into 3-5 concrete subtasks a student can complete "
        f"one at a time: \"{title}\" (due {due_date}). Description: "
        f"{description or 'none'}. Return STRICT JSON only — an object with one "
        "key \"subtasks\" — an array of objects each with \"title\" (short "
        "actionable phrase) and \"hours\" (estimated hours, 0.5-8). Cover the "
        "whole assignment; order subtasks logically.\n\n"
        "Example: {\"subtasks\": [{\"title\": \"Read the prompt and outline\", \"hours\": 1}]}"
    )


# ---------------------------------------------------------------------------
# Phase 7 — AI Tutor & Assessment (Ideas 61–70)
# ---------------------------------------------------------------------------

def tutor_chat_prompt(
    message: str,
    context: str,
    *,
    memory: dict | None = None,
    history: str = "",
    insist_cite: bool = False,
    known_context: list[dict] | None = None,
    # Phase 10 (Ideas 92/95): compact durable-facts + learner-context blocks.
    durable_facts: str = "",
    learner_context: str = "",
) -> str:
    """Prompt for a RAG-grounded tutor answer (Idea 61, phrase 4).

    ``context`` is the numbered chunk block built by ``tutor.context_blocks``.
    The model MUST cite ``[source: path]`` for every claim (Rule A) or say it
    does not know. ``insist_cite`` tightens the instruction for the one-shot
    citation-check retry (phrase 7).

    Phase 8 (Idea 74): ``known_context`` is a list of ``{concept, strength,
    last_seen}`` rows from ``user_memory`` (phrase 32). The prompt only then
    authorises the reference phrasing "as you saw in your notes on X" — and
    only for concepts in that list, never invented (phrase 33, Rule A).
    """
    cite_rule = (
        "CRITICAL: your previous answer had no citations. Rewrite it so EVERY "
        "claim carries a [source: path] marker from the excerpts below."
        if insist_cite
        else "Every claim must carry a [source: path] marker pointing at the "
        "excerpt it came from."
    )
    memory_block = ""
    if memory and (memory.get("strengths") or memory.get("weaknesses")):
        memory_block = (
            "Known strengths: " + ", ".join(memory.get("strengths") or []) + "\n"
            "Known weaknesses: " + ", ".join(memory.get("weaknesses") or []) + "\n"
        )
    known_block = ""
    if known_context:
        lines = []
        for k in known_context:
            seen = f" (last seen {k.get('last_seen', 'earlier')})" if k.get("last_seen") else ""
            lines.append(f"- {k.get('concept', '')}{seen}")
        known_block = (
            "Concepts this student has already studied (from their own "
            "memory — the ONLY prior knowledge you may assume):\n"
            + "\n".join(lines)
            + "\n\nYou MAY say \"as you saw in your notes on X\" but ONLY for "
            "concepts in this list. Never claim the student knows anything else.\n"
        )
    history_block = f"\nRecent conversation:\n{history}\n" if history else ""
    p10_block = "\n\n".join(b for b in (durable_facts, learner_context) if b)
    p10_block = f"\n\n{p10_block}" if p10_block else ""
    return (
        "You are a tutor who answers ONLY from the student's own Second Brain "
        "notes. Use the numbered excerpts below. "
        f"{cite_rule} If the excerpts do not cover the question, say \"I don't "
        "have this in your Second Brain\" and suggest capturing a note — never "
        "invent facts. Keep the answer focused and readable (2-6 sentences, "
        "short lists where helpful).\n\n"
        f"{known_block}{memory_block}{history_block}{p10_block}"
        f"Excerpts:\n{context}\n\n"
        f"Student question: {message}"
    )


def tutor_doubt_prompt(
    question: str,
    step_where_stuck: str | None,
    context: str,
    gap_line: str,
) -> str:
    """Prompt for gap-first doubt resolution (Idea 62, phrase 13–14)."""
    return (
        "A student is stuck on a step of a problem. First explain the blocking "
        "concept (the gap) clearly using the excerpts, THEN re-walk the original "
        "problem step by step from that gap. Ground every claim in the excerpts "
        "with [source: path] markers; never invent steps.\n\n"
        f"Problem: {question}\n"
        f"Stuck at: {step_where_stuck or 'a step'}\n"
        f"Detected gap / prerequisite: {gap_line}\n\n"
        f"Excerpts:\n{context}"
    )


def practice_questions_prompt(
    topic_name: str,
    outcomes: list[str],
    count: int,
    difficulty: str,
    chunks: str,
) -> str:
    """Prompt for a reviewable practice-question bank (Idea 63, phrase 23)."""
    outcome_line = "; ".join(outcomes) or "none listed"
    return (
        f"Write {count} multiple-choice practice questions about \"{topic_name}\" "
        f"at {difficulty} difficulty. Each must test one learning outcome. Return "
        "STRICT JSON only — an object with one key \"questions\" — an array of "
        "objects each with \"q\" (question), \"options\" (exactly 4 strings), "
        "\"answer\" (the correct option text), \"explanation\" (one sentence), "
        "and \"bloom_level\" (one of Remember, Understand, Apply, Analyze, "
        "Evaluate, Create). Ground questions in the notes when possible.\n\n"
        f"Topic: {topic_name}\nOutcomes: {outcome_line}\n\n"
        f"Notes:\n{chunks}"
    )


def grading_prompt(
    question: str,
    expected: str,
    answer: str,
    rubric: str,
) -> str:
    """Prompt for advanced partial-credit grading (Idea 66, phrase 52–53)."""
    return (
        "Grade the student's answer against the rubric below. Award partial "
        "credit: the score must reflect how many key points are covered, not "
        "all-or-nothing. Return STRICT JSON only with exactly four keys: "
        "\"score\" (integer 0-100), \"strengths\" (array of short strings), "
        "\"misconceptions\" (array of short strings), and \"action_items\" "
        "(array of short study actions).\n\n"
        f"Question: {question}\nExpected answer: {expected}\n"
        f"Student answer: {answer}\nRubric / key points:\n{rubric}"
    )


def mistake_analysis_prompt(
    question: str,
    model_solution: str,
    student_answer: str,
    chunks: str,
) -> str:
    """Prompt for explain-my-mistake walkthroughs (Idea 68, phrase 72)."""
    return (
        "The student answered a practice question incorrectly. Pinpoint where "
        "their reasoning diverged from the model solution: which key point or "
        "step they missed. Then recommend which note to re-read. Return STRICT "
        "JSON only with exactly three keys: \"divergence\" (one short paragraph), "
        "\"missed_points\" (array of short strings), and \"recommendation\" "
        "(one sentence naming the note to re-read).\n\n"
        f"Question: {question}\nModel solution: {model_solution}\n"
        f"Student answer: {student_answer}\n\nNotes:\n{chunks}"
    )


def skill_mapping_prompt(subject: str, topics: list[str]) -> str:
    """Prompt for topic→skill mapping (Idea 70, phrase 94)."""
    listing = "\n".join(f"- {t}" for t in topics) or "(no topics)"
    return (
        f"Map each topic of the course \"{subject}\" to skills from this "
        "taxonomy. Return STRICT JSON only — an object with one key "
        "\"mappings\" — an array of objects each with \"topic\" (exact topic "
        "name) and \"skill_id\" (the closest taxonomy skill id). Only use "
        "skill ids from the taxonomy; skip topics with no good match.\n\n"
        f"Taxonomy:\n{taxonomy_listing()}\n\n"
        f"Topics:\n{listing}"
    )


def taxonomy_listing() -> str:
    """Inline skill taxonomy for prompts — lazy import keeps prompt module lean."""
    try:
        from app.services.kb.skills import load_taxonomy

        tax = load_taxonomy()
        return "\n".join(f"- {s['id']}: {s['name']}" for s in tax.get("skills", []))
    except Exception:  # noqa: BLE001
        return "(taxonomy unavailable)"


# ---------------------------------------------------------------------------
# Phase 8 — Personalization & Learning Memory (Ideas 71–80)
# ---------------------------------------------------------------------------

def contradiction_prompt(old_title: str, old_text: str, new_title: str, new_text: str) -> str:
    """Prompt for an outdated-note contradiction verdict (Idea 78, phrase 73).

    Two similar vault documents where one is newer. The model must return
    ``{verdict, reason}`` with verdict one of contradicts | supports | unrelated.
    """
    return (
        "Two notes from a student's vault are about the same topic. The second "
        "was written later. Decide whether the NEWER note contradicts the OLDER "
        "one. Return STRICT JSON only with two keys: \"verdict\" (exactly one of "
        "\"contradicts\", \"supports\", \"unrelated\") and \"reason\" (one short "
        "sentence, or null). Verdict \"contradicts\" only when the newer note "
        "asserts something the older note denies or that cannot both be true.\n\n"
        f"OLDER note ({old_title}):\n{old_text}\n\n"
        f"NEWER note ({new_title}):\n{new_text}"
    )


def explain_prompt_personalized(
    concept: str,
    depth: str,
    context: str,
    doc_titles: list[tuple[int, str]],
    *,
    anchors: list[str] | None = None,
    profile_line: str = "",
) -> str:
    """Grounded explanation that builds on the user's known concepts (Idea 73).

    ``anchors`` are concepts present in ``user_memory`` (Rule A) the explanation
    may reference as prior knowledge; ``profile_line`` is the rendered
    ``preferences_prompt`` output. Both are empty when memory/preferences are
    empty, so the prompt degrades to the standard grounded explanation.
    """
    base = explain_prompt(concept, depth, context, doc_titles)
    extra: list[str] = []
    if anchors:
        extra.append(
            "The student already knows these concepts (from their own notes): "
            + ", ".join(anchors)
            + ". Where helpful, explain \"" + concept + "\" by building on "
            "those known concepts — say \"you already know X, so think of this "
            "as …\" — but never claim the student knows anything else."
        )
    if profile_line:
        extra.append(profile_line)
    if not extra:
        return base
    return base + "\n\n" + "\n\n".join(extra)

