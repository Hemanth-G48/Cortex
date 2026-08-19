"""AI capability + generation endpoints.

Every feature endpoint:
1. Tries the OpenAI-compatible provider via ``services.ai_client``.
2. Falls back to a deterministic local generator (``services.ai_fallback``)
   when AI is disabled, unreachable, or returns unparseable output.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Assignment, Course, User
from app.services import ai_cache, ai_client, ai_fallback, ai_providers, embeddings
from app.services.users import current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])

# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


@router.get("/health")
def ai_health() -> dict:
    active = ai_providers.get_registry().active()
    return {
        "available": ai_client.ai_available(),
        "mode": "AI" if ai_client.ai_available() else "Offline (deterministic fallback)",
        "model": (active.model if active else None) if ai_client.ai_available() else None,
        "models": ai_client.ai_models() if ai_client.ai_available() else [],
        # Provider registry: which provider is active and how to reach it.
        "active_provider": ai_providers.mask_config(active) if active else None,
        "providers_count": len(ai_providers.get_registry().all()),
        # Phase 2 (Idea 11): embeddings capability surfaced for the UI footer.
        "embeddings": {
            "available": embeddings.embed_available(),
            "model": settings.EMBEDDINGS_MODEL if embeddings.embed_available() else None,
            "dim": settings.EMBEDDINGS_DIM,
            "batch_size": settings.EMBEDDINGS_BATCH_SIZE,
            "backend": settings.VECTOR_STORE_BACKEND,
        },
        # QuestLog (Idea 95): AI response cache status (mirrors getAIStatus).
        "cache": ai_cache.cache_stats(),
    }


@router.get("/models")
def ai_models() -> dict:
    active = ai_providers.get_registry().active()
    return {
        "models": ai_client.ai_models(),
        "enabled": ai_client.ai_available(),
        # Backwards-compatible extra: active provider + per-provider models.
        "active_provider": ai_providers.mask_config(active) if active else None,
        "providers": [ai_providers.mask_config(p) for p in ai_providers.get_registry().all()],
    }


# ---------------------------------------------------------------------------
# Provider registry management (local-first, single-user)
# ---------------------------------------------------------------------------


class ProviderCreate(BaseModel):
    name: str
    provider_type: str = "custom"  # custom | openai | ollama | lmstudio | anthropic | google
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    enabled: bool = True
    is_default: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # empty/None → leave unchanged
    model: str | None = None
    enabled: bool | None = None
    is_default: bool | None = None


@router.get("/providers")
def list_providers() -> dict:
    """All configured providers with masked credentials (never raw API keys)."""
    registry = ai_providers.get_registry()
    return {
        "providers": [ai_providers.mask_config(p) for p in registry.all()],
        "active_id": registry.active().id if registry.active() else None,
    }


@router.post("/providers", status_code=201)
def create_provider(data: ProviderCreate) -> dict:
    registry = ai_providers.get_registry()
    config = registry.create(
        name=data.name,
        provider_type=data.provider_type,
        base_url=data.base_url,
        api_key=data.api_key,
        model=data.model,
        enabled=data.enabled,
        is_default=data.is_default,
    )
    return ai_providers.mask_config(config)


@router.put("/providers/{provider_id}")
def update_provider(provider_id: str, data: ProviderUpdate) -> dict:
    registry = ai_providers.get_registry()
    config = registry.update(
        provider_id,
        name=data.name,
        provider_type=data.provider_type,
        base_url=data.base_url,
        api_key=data.api_key,
        model=data.model,
        enabled=data.enabled,
        is_default=data.is_default,
    )
    if config is None:
        from fastapi import HTTPException

        raise HTTPException(404, "Provider not found")
    return ai_providers.mask_config(config)


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str) -> dict:
    registry = ai_providers.get_registry()
    ok = registry.remove(provider_id)
    from fastapi import HTTPException

    if not ok:
        raise HTTPException(404, "Provider not found")
    return {"ok": True}


@router.post("/providers/{provider_id}/test")
def test_provider(provider_id: str) -> dict:
    """Live connection test against the provider (short timeout)."""
    return ai_providers.get_registry().test(provider_id)


@router.post("/providers/{provider_id}/refresh-models")
def refresh_provider_models(provider_id: str) -> dict:
    """Fetch the provider's current model list and persist it."""
    from fastapi import HTTPException

    config = ai_providers.get_registry().refresh_models(provider_id)
    if config is None:
        raise HTTPException(404, "Provider not found")
    return ai_providers.mask_config(config)


@router.post("/providers/{provider_id}/default")
def set_default_provider(provider_id: str) -> dict:
    """Mark this provider as the active/default one."""
    from fastapi import HTTPException

    config = ai_providers.get_registry().set_default(provider_id)
    if config is None:
        raise HTTPException(404, "Provider not found")
    return ai_providers.mask_config(config)


class CompleteRequest(BaseModel):
    prompt: str
    max_tokens: int = 2048
    temperature: float = 0.7
    model: str | None = None


class CompleteResponse(BaseModel):
    text: str
    ai_used: bool


@router.post("/complete", response_model=CompleteResponse)
def ai_complete(data: CompleteRequest) -> CompleteResponse:
    text = ai_client.generate(
        data.prompt, max_tokens=data.max_tokens, temperature=data.temperature, model=data.model
    )
    if text is None:
        # Deterministic echo fallback keeps the endpoint useful offline.
        return CompleteResponse(text=data.prompt[:500], ai_used=False)
    return CompleteResponse(text=text, ai_used=True)


# ---------------------------------------------------------------------------
# Feature generation (deterministic fallback when AI unavailable)
# ---------------------------------------------------------------------------


class QuizRequest(BaseModel):
    content: str | None = None


@router.post("/quiz")
def ai_quiz(data: QuizRequest) -> dict:
    prompt = (
        'Generate 5 multiple choice questions from this content. Return ONLY a JSON array, '
        'no markdown: [{"q":"...","opts":["a","b","c","d"],"ans":0}]\n\n' + (data.content or "")
    )
    parsed = ai_client.generate_json(prompt, max_tokens=1200) if ai_client.ai_available() else None
    questions = parsed if isinstance(parsed, list) and len(parsed) > 0 else ai_fallback.demo_quiz(data.content)
    return {"questions": questions, "ai_used": parsed is not None}


class FlashcardsRequest(BaseModel):
    content: str | None = None
    topic: str | None = None
    difficulty: str = "basic"


@router.post("/flashcards")
def ai_flashcards(data: FlashcardsRequest) -> dict:
    difficulty_prompt = {
        "easy": "very easy, recall-level basics a beginner would know",
        "basic": "straightforward, fundamental concepts",
        "medium": "moderately challenging, requires real understanding",
        "hard": "hard, requires connecting multiple concepts",
        "olympic": "olympiad-style — the hardest, most advanced questions, the kind used in academic competitions",
    }.get(data.difficulty, "straightforward, fundamental concepts")

    prompt = (
        f'From the following study material, write 8 high-quality flashcard question/answer pairs at '
        f'a {difficulty_prompt} difficulty level. Return ONLY a JSON array, no markdown, no explanation: '
        f'[{{"front":"question here","back":"answer here"}}, ...]\n\nMaterial:\n'
        f'{(data.content or data.topic or "")[:4000]}'
    )
    parsed = ai_client.generate_json(prompt, max_tokens=1600) if ai_client.ai_available() else None
    cards = (
        [c for c in parsed if isinstance(c, dict) and c.get("front") and c.get("back")]
        if isinstance(parsed, list) and len(parsed) > 0
        else ai_fallback.demo_flashcards(data.topic, data.difficulty)["cards"]
    )
    return {"cards": cards, "ai_used": isinstance(parsed, list)}


class StudyPlanRequest(BaseModel):
    subject: str
    exam_date: str | None = None


@router.post("/study-plan")
def ai_study_plan(data: StudyPlanRequest) -> dict:
    prompt = (
        f'Create a 4-week study plan for "{data.subject}" with exam on {data.exam_date or "TBD"}. '
        f'Return ONLY JSON, no markdown: {{"subject":"...","weeks":[{{"week":1,"topic":"...","tasks":["a","b","c"]}}]}}'
    )
    parsed = ai_client.generate_json(prompt) if ai_client.ai_available() else None
    plan = parsed if isinstance(parsed, dict) and isinstance(parsed.get("weeks"), list) else ai_fallback.demo_study_plan(data.subject, data.exam_date)
    plan["subject"] = data.subject
    plan["exam_date"] = data.exam_date
    return {"plan": plan, "ai_used": isinstance(parsed, dict)}


class SyllabusRequest(BaseModel):
    text: str


@router.post("/syllabus")
def ai_syllabus(data: SyllabusRequest) -> dict:
    prompt = (
        'Extract all assignments and due dates from this syllabus. Return ONLY a JSON array, no markdown: '
        '[{"title":"...","dueDate":"YYYY-MM-DD","course":"...","priority":"low|medium|high"}]\n\n' + data.text
    )
    parsed = ai_client.generate_json(prompt) if ai_client.ai_available() else None
    items = (
        [i for i in parsed if isinstance(i, dict) and i.get("title")]
        if isinstance(parsed, list) and len(parsed) > 0
        else ai_fallback.demo_syllabus(data.text)
    )
    # Normalise dueDate → due_date for the Assignment model.
    for item in items:
        if "dueDate" in item and "due_date" not in item:
            item["due_date"] = item.pop("dueDate")
    return {"assignments": items, "ai_used": isinstance(parsed, list)}


class GradeAnswerRequest(BaseModel):
    question: str
    expected: str
    answer: str
    # Phase 7 (Idea 66, phrase 51): "basic" (backward-compatible) or
    # "advanced" — partial credit + structured feedback. Optional so the
    # existing flashcard flow keeps working unchanged.
    mode: str = "basic"
    topic_id: int | None = None


class InsightsRequest(BaseModel):
    # True = explicit user refresh: recompute + re-persist. False (default)
    # = return the persisted snapshot — opening the dashboard never spends a
    # model call.
    force: bool = False


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
    should_generate_plan: bool = False
    ai_used: bool = False


@router.post("/insights")
def ai_insights(body: InsightsRequest | None = None, db: Session = Depends(get_db)) -> dict:
    """Persisted productivity insights from real user stats (QuestLog pattern).

    The last generated insight is stored per user and reused on every request
    (``cached=True`` + ``analyzed_at``) — opening the dashboard never triggers
    an LLM call. The provider is only consulted when no snapshot exists yet
    (first run) or the user explicitly asks for a refresh (``force=True``).
    Deterministic fallback keeps the endpoint functional when AI is disabled.
    """
    from app.services.ai_insights import get_insights

    user = db.query(User).first()
    result = get_insights(db, user, force=bool(body and body.force))
    db.commit()
    return result


@router.post("/chat", response_model=ChatResponse)
def ai_chat(data: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Context-aware AI study companion (Phase 62).

    Builds a system prompt from the student's real DB data (assignments,
    courses, user), tries the provider, then falls back to the local
    heuristic responder (Phase 63) when AI is unavailable.
    """
    assignments = db.query(Assignment).all()
    courses = db.query(Course).all()
    user = db.query(User).first()

    pending = [a for a in assignments if getattr(a, "status", None) != "Completed"]
    upcoming = sorted(
        (a for a in assignments if getattr(a, "due_date", None)),
        key=lambda a: str(a.due_date),
    )[:5]
    course_titles = [c.title for c in courses if c.title]
    subjects_text = ", ".join(course_titles[:5]) or "your courses"
    course_names = {c.id: c.title for c in courses}

    deadline_lines = "\n".join(
        f'• {a.title} ({course_names.get(a.course_id, "Unknown")}) due {a.due_date}'
        for a in upcoming
    ) or "none"

    context_prompt = (
        "You are Shiori (栞), a warm and knowledgeable AI study companion for students. "
        f"You have access to the student's current academic data:\n"
        f"- Total assignments: {len(assignments)}\n"
        f"- Pending assignments: {len(pending)}\n"
        f"- Subjects: {subjects_text}\n"
        f"- Upcoming deadlines: {deadline_lines}\n\n"
        "Keep responses concise (2-4 sentences), encouraging, and actionable. "
        "Use the student's actual data in your responses."
    )

    lower = (data.message or "").lower()
    wants_plan = (
        ("generate" in lower or "create" in lower)
        and any(k in lower for k in ("study", "plan", "schedule"))
    ) or ("plan" in lower and "study" in lower)

    # 1) Try the AI provider.
    if ai_client.ai_available():
        prompt = f"{context_prompt}\n\nStudent: {data.message}"
        text = ai_client.generate(prompt, max_tokens=600)
        if text:
            return ChatResponse(
                message=text,
                should_generate_plan=wants_plan and len(pending) > 0,
                ai_used=True,
            )

    # 2) Deterministic local fallback (Phase 63).
    context = {
        "assignments": [
            {"title": a.title, "due_date": str(a.due_date) if a.due_date else None, "course_id": a.course_id, "status": a.status}
            for a in assignments
        ],
        "courses": [{"id": c.id, "title": c.title} for c in courses],
        "user": {"current_level": user.current_level if user else None, "total_xp": user.total_xp if user else 0},
    }
    result = ai_fallback.local_chat_response(data.message, context)
    return ChatResponse(message=result["message"], should_generate_plan=wants_plan and len(pending) > 0)


@router.post("/grade-answer")
def ai_grade_answer(
    data: GradeAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user),
) -> dict:
    if data.mode == "advanced":
        # Phase 7 (Idea 66): partial credit + structured feedback, persisted to
        # the owner's learning events.
        from app.services.kb.grading import grade_answer

        result = grade_answer(
            db,
            current_user.id,
            data.question,
            data.expected,
            data.answer,
            topic_id=data.topic_id,
        )
        db.commit()
        return {**result["grade"], "ai_used": result["ai_used"], "mode": "advanced"}

    prompt = (
        f'You are grading a student\'s flashcard answer. Question: "{data.question}"\n'
        f'Expected answer: "{data.expected}"\nStudent\'s answer: "{data.answer}"\n\n'
        'Judge if the student\'s answer is correct — accept answers that are substantively correct even if worded differently. '
        'Return ONLY JSON, no markdown: {"correct": true or false, "explanation": "one short sentence explaining why, '
        'and the correct answer if they got it wrong"}'
    )
    parsed = ai_client.generate_json(prompt, max_tokens=300) if ai_client.ai_available() else None
    if isinstance(parsed, dict) and isinstance(parsed.get("correct"), bool):
        return {"correct": parsed["correct"], "explanation": parsed.get("explanation", ""), "ai_used": True}
    return {**ai_fallback.demo_grade_answer(data.question, data.expected, data.answer), "ai_used": False}
