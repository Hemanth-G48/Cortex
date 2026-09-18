from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./student_os.db"
    APP_NAME: str = "Student Life OS"
    VERSION: str = "0.1.0"

    # ── AI provider (OpenAI-compatible → OmniRoute by default) ──
    AI_BASE_URL: str = "http://localhost:20128/v1"
    AI_API_KEY: str = "omniroute-local"
    AI_MODEL: str = "oc/deepseek-v4-flash-free"
    # Comma-separated fallback models tried in order when the primary fails.
    AI_MODELS_FALLBACK: str = ""
    # Master switch — when False every AI path short-circuits to deterministic
    # local fallbacks so CI/tests never touch the network.
    AI_ENABLED: bool = True
    # Optional path override for the AI provider registry JSON (defaults to
    # ``app/data/ai_providers.json``). Providers are edited via /api/ai/* or
    # by hand; the env vars above remain the implicit fallback provider.
    AI_PROVIDERS_FILE: str = ""

    # ── Google OAuth (read-only Classroom/Gmail/Calendar scopes) ──
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ── Courses (dynamic source derivation) ──
    # Second Brain documents tagged with this prefix group into one Course per
    # tag (e.g. `course:Operating Systems` → a course titled "Operating Systems").
    COURSE_TAG_PREFIX: str = "course:"

    # ── Test-only auth (single-user app) ──
    # The application is single-user and tokenless: no login, no roles, no
    # bearer tokens. These settings exist solely so the pytest-only auth shim
    # (``app/routers/auth.py``) and the legacy test suite's signup/login
    # helpers keep working. They are never used by the application itself.
    APP_SECRET: str = "student-os-dev-secret"
    # Secret key the test shim checks when a test signs up a "teacher" role
    # (empty → teacher signups rejected, even under pytest).
    TEACHER_SECRET_KEY: str = ""

    # ── AI response cache (QuestLog, Idea 95) ──
    # In-memory TTL cache for AI completions, mirroring QuestLog's
    # ``ai.controller.js`` NodeCache pattern (stdTTL 600s). Identical prompts
    # within the TTL window are served from cache instead of hitting the
    # provider — cutting cost/latency on repeated calls (dashboard insights,
    # study tips). Keys embed the full prompt (which already carries per-user
    # context), so responses stay per-user correct.
    AI_CACHE_ENABLED: bool = True
    AI_CACHE_TTL_SECONDS: int = 600
    # Bounded eviction — when full, the oldest entry is dropped.
    AI_CACHE_MAX_ENTRIES: int = 200

    # ── File uploads (STUDENT-PLANAR G1: Phase 5) ──
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 10
    # Book PDFs (textbooks, security manuals, etc.) are commonly far larger
    # than course materials, so the reading tracker gets its own higher cap.
    # Env-overridable via BOOK_MAX_UPLOAD_MB.
    BOOK_MAX_UPLOAD_MB: int = 100

    # ── Vector store (Zenith-Study-Planner G1; Second Brain Phase 2) ──
    # "numpy" (default, in-memory) | "faiss" (optional faiss-cpu) |
    # "file" (Phase 2, dev — file-backed numpy store under UPLOAD_DIR/kb_index) |
    # "pgvector" (Phase 2, prod — import-guarded pgvector column in kb_embeddings).
    VECTOR_STORE_BACKEND: str = "numpy"

    # ── SyllabusAI (G13 Phase 87): summary cost guard ──
    # Max non-cached summary generations per day (LLM cost guard). The
    # deterministic demo fallback is exempt (AI_ENABLED=False skips the cap).
    SUMMARY_DAILY_LIMIT: int = 10

    # ── Sleep tracker (Zenith-Study-Planner G3) ──
    # Target nightly sleep hours used by the bedtime recommendation engine.
    DEFAULT_SLEEP_TARGET_HOURS: float = 8.0

    # ── Second Brain / Knowledge Core (Phase 1) ──
    # Folder watcher: poll enabled sources every N seconds. Set false in CI or
    # when vaults are scanned on demand.
    KB_WATCH_ENABLED: bool = True
    KB_WATCH_POLL_INTERVAL: int = 30
    # Semantic chunking (Idea 7): target chunk size and overlap in characters.
    KB_CHUNK_SIZE: int = 1200
    KB_CHUNK_OVERLAP: int = 150
    # OCR (Idea 6): disabled by default; requires pytesseract + pdf2image +
    # Pillow plus system tesseract/poppler binaries. Gracefully no-ops when off.
    KB_OCR_ENABLED: bool = False
    KB_TESSERACT_CMD: str = ""
    # Max versions kept per document (Idea 9, phrase 85).
    KB_MAX_VERSIONS: int = 20
    # Snapshot-at path threshold (chars) — larger documents snapshot to disk.
    KB_SNAPSHOT_DISK_CHARS: int = 100_000

    # ── Second Brain / Phase 2 (Embeddings, Indexing & Knowledge Graph) ──
    # Embeddings provider (Idea 11): OpenAI-compatible /embeddings endpoint
    # served by the same AI_BASE_URL as chat completions.
    EMBEDDINGS_MODEL: str = "text-embedding-3-small"
    EMBEDDINGS_DIM: int = 384  # Match all-MiniLM-L6-v2 for fastembed GPU
    EMBEDDINGS_BATCH_SIZE: int = 32
    # Embedding backend selection: "provider" (OpenAI-compatible /embeddings,
    # default), "fastembed" (local ONNX model via fastembed — offline, no
    # PyTorch), or "auto" (provider first, then fastembed). "hash" forces the
    # deterministic local fallback. When fastembed is used, EMBEDDINGS_DIM must
    # match the local model (all-MiniLM-L6-v2 = 384).
    EMBEDDINGS_BACKEND: str = "fastembed"
    # Local sentence model used when EMBEDDINGS_BACKEND is fastembed/auto.
    # Using BAAI/bge-small-en-v1.5 for fast local inference (384 dim)
    EMBEDDINGS_LOCAL_MODEL: str = "BAAI/bge-small-en-v1.5"
    # Per-day LLM embedding budget (cost guard, mirrors SUMMARY_DAILY_LIMIT).
    EMBEDDINGS_DAILY_LIMIT: int = 1000
    # Min weight for an edge to appear in the knowledge graph (Idea 16).
    KB_EDGE_MIN_WEIGHT: float = 0.3
    # Document-pair cosine threshold for inferred RELATED edges (Idea 17).
    KB_SIM_THRESHOLD: float = 0.75
    # Per-day budget for dependency-edge LLM passes (Idea 17).
    KB_INFER_DAILY_BUDGET: int = 100
    # Near-duplicate detection (Idea 19): cosine threshold + method.
    KB_NEARDUP_THRESHOLD: float = 0.95
    # embedding (default, exact over kb_embeddings) | minhash (datasketch LSH).
    KB_NEARDUP_METHOD: str = "embedding"
    # Exclude near-dup chunks from retrieval by default (Phase 3 readiness).
    KB_EXCLUDE_NEARDUP: bool = True

    # ── Second Brain / Phase 3 (Search & Retrieval) ──
    # Full-text search (Idea 21): SQLite FTS5 virtual table over kb_chunks.
    KB_FTS_ENABLED: bool = True
    # Minimum token length included in the FTS index (shorter = more noise).
    KB_FTS_MIN_TOKEN: int = 2
    # Default retrieval mode (Idea 23): keyword | semantic | hybrid.
    KB_SEARCH_MODE: str = "hybrid"
    # RRF fusion constant (Idea 23): score = sum(1/(k + rank)).
    KB_RRF_K: int = 60
    # Query expansion (Idea 24) — kill switch so the eval harness can compare
    # expanded vs raw behavior.
    KB_QUERY_EXPANSION_ENABLED: bool = True
    # Health analysis (Idea 27): a note is "stale" when untouched for this many
    # days and never re-visited.
    KB_STALE_DAYS: int = 90
    # Missing-knowledge gaps (Idea 28): coverage below this fraction is a gap.
    KB_GAP_THRESHOLD: float = 0.2
    # Search feedback learning (Idea 29) — ships default-off until the eval
    # harness proves weight adjustments improve recall@k / MRR.
    KB_LEARNING_ENABLED: bool = False

    # ── Second Brain / Phase 4 (Note Intelligence & Content Generation) ──
    # Budget cap for ALL Phase 4 AI generation (document summaries,
    # explanations, note quizzes, flashcard candidates, quality suggestions,
    # brain-dump splitting) per user per day — extends the SUMMARY_DAILY_LIMIT
    # guard pattern. Deterministic fallbacks are exempt (they never hit the
    # provider), mirroring the demo-summary exemption.
    KB_DAILY_GEN_LIMIT: int = 20
    # Note-quality scoring (Idea 39): weight per component. Must sum to 1.0;
    # the ``kb_quality_weights`` property re-normalizes defensively.
    KB_QUALITY_WEIGHTS: dict[str, float] = {
        "length": 0.25,
        "headings": 0.2,
        "links": 0.25,
        "recency": 0.1,
        "coverage": 0.2,
    }
    # A note is "fresh" for the quality recency component when touched within
    # this many days (Idea 39, phrase 82).
    KB_QUALITY_FRESH_DAYS: int = 90

    # ── Second Brain / Phase 6 (Study Planning & Execution, Ideas 51–60) ──
    # Revision scheduling (Idea 52): SM-2 bounds and initial interval.
    KB_REVISION_INITIAL_INTERVAL: int = 1
    KB_REVISION_MIN_EASE: float = 1.3
    KB_REVISION_MAX_INTERVAL: int = 365
    # Attendance (Idea 56): N consecutive misses triggers a falling-pattern
    # alert notification.
    KB_ATTENDANCE_ALERT_STREAK: int = 3
    # Next-action recommender (Idea 59): factor weights. Must sum to ~1.0; the
    # ``kb_next_action_weights`` property re-normalizes defensively.
    KB_NEXT_ACTION_WEIGHTS: dict[str, float] = {
        "readiness": 0.35,
        "weakness": 0.3,
        "due_reviews": 0.2,
        "exam_proximity": 0.15,
    }

    # ── Second Brain / Phase 7 (AI Tutor & Assessment, Ideas 61–70) ──
    # Max vault chunks injected into one tutor answer (Idea 61, phrase 3).
    KB_TUTOR_MAX_CHUNKS: int = 6
    # Rolling tutor-history window: how many past assistant turns stay in the
    # prompt context (phrase 8).
    KB_TUTOR_HISTORY_TURNS: int = 4
    # Practice question generation (Idea 63): default count per topic.
    KB_PRACTICE_DEFAULT_COUNT: int = 5
    # Mock tests (Idea 64): max duration in minutes and default question count.
    KB_MOCK_DEFAULT_DURATION_MINS: int = 60
    KB_MOCK_DEFAULT_QUESTIONS: int = 10
    # Adaptive practice (Idea 67): accuracy thresholds that raise/lower the
    # difficulty tier after each answer (IRT-lite, phrase 63).
    KB_ADAPTIVE_RAISE_ACC: float = 0.7
    KB_ADAPTIVE_LOWER_ACC: float = 0.4
    # Capture/revision XP (Idea 69): amounts per trigger, zero-defaults so the
    # feature ships disabled for determinism (phrase 85).
    KB_XP_REWARDS: dict[str, int] = {
        "revision": 0,
        "daily_note": 0,
        "dump_filed": 0,
    }
    # Skill mapping (Idea 70): JSON taxonomy path + level thresholds.
    KB_SKILLS_JSON: str = "app/data/skills.json"
    KB_SKILL_STRONG: float = 0.75
    KB_SKILL_WEAK: float = 0.4

    # ── Second Brain / Phase 9 (Automation, Ideas 81–90) ──
    # Every automation is a scheduled background job behind a KB_AUTO_* toggle,
    # default OFF so adoption is gradual and CI stays hermetic. The unifying
    # pattern: batch job → proposals (with provenance) → review queue → apply
    # with version-history logging. Nothing auto-commits without review.
    #
    # Idea 81 — auto-categorize new notes into folders.
    KB_AUTO_CATEGORIZE_ENABLED: bool = False
    KB_AUTO_CATEGORIZE_PER_RUN: int = 20
    # Idea 82 — nightly auto-tag of untagged documents.
    KB_AUTO_TAG_ENABLED: bool = False
    KB_AUTO_TAG_PER_NIGHT: int = 20
    # Idea 83 — periodic auto-link of related notes (embedding clusters).
    KB_AUTO_LINK_ENABLED: bool = False
    KB_AUTO_LINK_PER_RUN: int = 50
    # Cosine bar above which a pair auto-creates an edge; below it the pair
    # waits in the review queue as a pending proposal.
    KB_AUTO_LINK_CONFIDENCE: float = 0.88
    # Idea 84 — nightly duplicate scan (exact + near).
    KB_AUTO_DUPE_ENABLED: bool = False
    KB_AUTO_DUPE_PER_NIGHT: int = 100
    # Idea 85 — auto-create flashcard candidates for concept-bearing notes.
    KB_AUTO_FLASHCARDS_ENABLED: bool = False
    KB_AUTO_FLASHCARDS_PER_RUN: int = 10
    # Idea 86 — nightly summary regeneration for changed docs.
    KB_AUTO_SUMMARY_ENABLED: bool = False
    KB_AUTO_SUMMARY_PER_NIGHT: int = 20
    # Idea 87 — batch mind-map pre-generation (outline-derived, no LLM cost).
    KB_AUTO_MINDMAP_ENABLED: bool = False
    KB_AUTO_MINDMAP_MIN_HEADINGS: int = 4
    # Idea 88 — auto-update study plans when material coverage shifts.
    KB_AUTO_PLAN_SYNC_ENABLED: bool = False
    # Min |delta| (as a fraction of a topic's estimate) before a plan revises,
    # preventing plan churn on small changes.
    KB_PLAN_DELTA_THRESHOLD: float = 0.2
    # Idea 89 — auto-sync external repositories (git | drive | clip).
    KB_SYNC_ENABLED: bool = False
    # Copy Recent Notes — dedicated scheduled job for ``sync_type='local'``
    # external vaults (mirror of a local Obsidian folder into notes/). Its own
    # toggle so the timer can keep the vault mirrored even when remote
    # repository sync (KB_SYNC_ENABLED) stays off.
    KB_AUTO_LOCAL_SYNC_ENABLED: bool = False
    # How often (seconds) the folder watcher fires the periodic automation
    # pass — the only timer the app has, so it drives ALL KB_AUTO_* jobs
    # (Copy Recent Notes, auto-tag, auto-summary, …). 0 disables the pass.
    KB_AUTO_RUN_INTERVAL_SECONDS: int = 3600
    # Idea 90 — daily materialization of due revision rows as tasks.
    KB_AUTO_REVISION_TASKS_ENABLED: bool = False
    # Dynamic courses — refresh Course rows from Second Brain `course:*` tags.
    # Default ON (unlike the other automation jobs): idempotent, no AI cost,
    # and only touches `source_type='kb_tag'` rows.
    KB_AUTO_COURSE_SYNC_ENABLED: bool = True

    # ── Second Brain / Phase 10 (Advanced AI, Analytics & Platform, Ideas 91–100) ──
    # Idea 92 — long-term memory: consolidate episodic events older than this
    # many days into durable facts (weekly job, budget-capped). Default OFF so
    # adoption is gradual and CI stays hermetic.
    KB_MEMORY_CONSOLIDATION_ENABLED: bool = False
    KB_MEMORY_CONSOLIDATION_DAYS: int = 7
    # Idea 93 — composable RAG pipeline: per-stage kill switches for A/B and
    # debugging. ``kb_rag_stages`` property re-normalizes defensively.
    KB_RAG_STAGES: dict[str, bool] = {
        "rewrite": True,
        "retrieve": True,
        "rerank": True,
        "verify": True,
        "faithfulness": True,
    }
    # Idea 94 — knowledge-graph + vector fusion: expansion depth + max added
    # candidates (perf guard, phrase 40).
    KB_GRAPH_EXPAND_HOPS: int = 2
    KB_GRAPH_EXPAND_CAP: int = 10
    # Idea 97 — cross-domain recommendation engine: per-factor weights
    # (urgency .4, weakness .3, readiness .3). ``kb_recommendation_weights``
    # property re-normalizes defensively.
    KB_RECOMMENDATION_WEIGHTS: dict[str, float] = {
        "urgency": 0.4,
        "weakness": 0.3,
        "readiness": 0.3,
    }
    # Idea 99 — trajectory forecasting: model + at-risk threshold.
    # ewma | linear
    KB_FORECAST_MODEL: str = "ewma"
    KB_FORECAST_RISK_THRESHOLD: float = 0.5
    # Idea 100 — observability: master switch for the ai_logs meter. When
    # False no row is written (tests/CI can disable for speed).
    KB_AI_LOG_ENABLED: bool = True

    # ── Second Brain / Phase 8 (Personalization & Learning Memory, Ideas 71–80) ──
    # Cross-subject "what to study next" recommender (Idea 75): per-factor weights.
    # Extends the Phase 6 per-topic KB_NEXT_ACTION_WEIGHTS with concept-gap + subject
    # coverage factors. Must sum to ~1.0; ``kb_recommend_weights`` re-normalizes.
    KB_RECOMMEND_WEIGHTS: dict[str, float] = {
        "readiness": 0.25,
        "weakness": 0.2,
        "due_reviews": 0.15,
        "concept_gaps": 0.2,
        "exam_proximity": 0.1,
        "subject_coverage": 0.1,
    }
    # Learning-memory strength half-life in days (Idea 79): unused concepts decay
    # exponentially toward zero; the default ≈ 3 months.
    KB_MEMORY_HALF_LIFE_DAYS: int = 90
    # A concept is a "known anchor" for explanations (Idea 73) above this strength.
    KB_MEMORY_ANCHOR_MIN: float = 0.4

    @property
    def kb_xp_rewards(self) -> dict[str, int]:
        """Sanitised capture-XP amounts — clamp to non-negative ints."""
        raw = self.KB_XP_REWARDS or {}
        return {
            key: max(0, int(raw.get(key, 0)))
            for key in ("revision", "daily_note", "dump_filed")
        }

    @property
    def kb_recommend_weights(self) -> dict[str, float]:
        """Sanitised Phase 8 recommender weights — clamp negatives, re-normalize."""
        weights = dict(self.KB_RECOMMEND_WEIGHTS or {})
        weights = {k: max(0.0, float(v)) for k, v in weights.items()}
        total = sum(weights.values())
        if total <= 0:
            return {
                "readiness": 0.25,
                "weakness": 0.2,
                "due_reviews": 0.15,
                "concept_gaps": 0.2,
                "exam_proximity": 0.1,
                "subject_coverage": 0.1,
            }
        return {k: round(v / total, 4) for k, v in weights.items()}

    @property
    def kb_memory_half_life_days(self) -> int:
        return max(1, int(self.KB_MEMORY_HALF_LIFE_DAYS))

    @property
    def kb_memory_anchor_min(self) -> float:
        return max(0.0, min(1.0, float(self.KB_MEMORY_ANCHOR_MIN)))

    @property
    def kb_memory_consolidation_days(self) -> int:
        return max(1, int(self.KB_MEMORY_CONSOLIDATION_DAYS))

    @property
    def kb_rag_stages(self) -> dict[str, bool]:
        """Sanitised RAG stage switches — known keys, booleans only."""
        stages = dict(self.KB_RAG_STAGES or {})
        return {
            stage: bool(stages.get(stage, True))
            for stage in ("rewrite", "retrieve", "rerank", "verify", "faithfulness")
        }

    @property
    def kb_recommendation_weights(self) -> dict[str, float]:
        """Sanitised recommendation weights — clamp negatives, re-normalize."""
        weights = dict(self.KB_RECOMMENDATION_WEIGHTS or {})
        weights = {k: max(0.0, float(v)) for k, v in weights.items()}
        total = sum(weights.values())
        if total <= 0:
            return {"urgency": 0.4, "weakness": 0.3, "readiness": 0.3}
        return {k: round(v / total, 4) for k, v in weights.items()}

    @property
    def kb_forecast_model(self) -> str:
        model = (self.KB_FORECAST_MODEL or "ewma").strip().lower()
        return model if model in ("ewma", "linear") else "ewma"

    @property
    def kb_forecast_risk_threshold(self) -> float:
        return max(0.0, min(1.0, float(self.KB_FORECAST_RISK_THRESHOLD)))

    @property
    def kb_next_action_weights(self) -> dict[str, float]:
        """Sanitised recommender weights — clamp negatives, re-normalize."""
        weights = dict(self.KB_NEXT_ACTION_WEIGHTS or {})
        weights = {k: max(0.0, float(v)) for k, v in weights.items()}
        total = sum(weights.values())
        if total <= 0:
            return {"readiness": 0.35, "weakness": 0.3, "due_reviews": 0.2, "exam_proximity": 0.15}
        return {k: round(v / total, 4) for k, v in weights.items()}

    @property
    def revision_initial_interval(self) -> int:
        return max(0, int(self.KB_REVISION_INITIAL_INTERVAL))

    @property
    def revision_min_ease(self) -> float:
        return max(1.0, float(self.KB_REVISION_MIN_EASE))

    @property
    def revision_max_interval(self) -> int:
        return max(1, int(self.KB_REVISION_MAX_INTERVAL))

    @property
    def kb_quality_weights(self) -> dict[str, float]:
        """Sanitised quality weights — clamp negatives, keep known keys, re-normalize."""
        weights = dict(self.KB_QUALITY_WEIGHTS or {})
        weights = {k: max(0.0, float(v)) for k, v in weights.items()}
        total = sum(weights.values())
        if total <= 0:
            return {"length": 0.25, "headings": 0.2, "links": 0.25, "recency": 0.1, "coverage": 0.2}
        return {k: round(v / total, 4) for k, v in weights.items()}

    @property
    def kb_tesseract_cmd(self) -> str | None:
        """Configured tesseract binary path, or None to let pytesseract find it."""
        return self.KB_TESSERACT_CMD.strip() or None

    model_config = {"env_file": ".env"}

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return max(int(self.MAX_UPLOAD_MB), 1) * 1024 * 1024

    @property
    def book_max_upload_bytes(self) -> int:
        """Maximum book (PDF) upload size in bytes."""
        return max(int(self.BOOK_MAX_UPLOAD_MB), 1) * 1024 * 1024

    @property
    def sleep_target_hours(self) -> float:
        """Sanitised sleep target, clamped to a healthy 4–14h range."""
        target = float(self.DEFAULT_SLEEP_TARGET_HOURS)
        return max(4.0, min(14.0, target))

    @property
    def ai_model_list(self) -> list[str]:
        """Primary model + comma-separated fallbacks (deduped, order preserved)."""
        models = [self.AI_MODEL]
        for name in (self.AI_MODELS_FALLBACK or "").split(","):
            name = name.strip()
            if name and name not in models:
                models.append(name)
        return models


settings = Settings()
