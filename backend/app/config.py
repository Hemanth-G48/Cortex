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

    # ── Google OAuth (read-only Classroom/Gmail/Calendar scopes) ──
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ── Role auth (STUDENT-PLANAR G1: secret used to sign bearer tokens) ──
    APP_SECRET: str = "student-os-dev-secret"
    # Secret key a user must supply to sign up as a teacher (empty → teacher
    # signups rejected).
    TEACHER_SECRET_KEY: str = ""

    # ── File uploads (STUDENT-PLANAR G1: Phase 5) ──
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 10

    # ── Vector store (Zenith-Study-Planner G1) ──
    # "numpy" (default) or "faiss" (requires the optional faiss-cpu package).
    VECTOR_STORE_BACKEND: str = "numpy"

    # ── SyllabusAI (G13 Phase 87): summary cost guard ──
    # Max non-cached summary generations per day (LLM cost guard). The
    # deterministic demo fallback is exempt (AI_ENABLED=False skips the cap).
    SUMMARY_DAILY_LIMIT: int = 10

    # ── Sleep tracker (Zenith-Study-Planner G3) ──
    # Target nightly sleep hours used by the bedtime recommendation engine.
    DEFAULT_SLEEP_TARGET_HOURS: float = 8.0

    model_config = {"env_file": ".env"}

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return max(int(self.MAX_UPLOAD_MB), 1) * 1024 * 1024

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
