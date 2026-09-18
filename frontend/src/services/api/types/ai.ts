// AI provider + generation types.
// Extracted from services/api.ts (F8 split).

// Configurable AI provider (local-first provider registry).
export type AIProviderType = 'custom' | 'openai' | 'ollama' | 'lmstudio' | 'anthropic' | 'google';

export interface AIProviderConfig {
  id: string;
  name: string;
  provider_type: AIProviderType;
  is_local: boolean;
  base_url: string;
  has_api_key: boolean;
  api_key_preview: string | null;
  model: string | null;
  models: string[];
  enabled: boolean;
  is_default: boolean;
}

export interface AIProviderTestResult {
  ok: boolean;
  message: string;
  latency_ms?: number;
  models?: string[];
}

export interface AIProvidersResponse {
  providers: AIProviderConfig[];
  active_id: string | null;
}

export interface AIHealth {
  available: boolean;
  mode: string;
  model: string | null;
  models: string[];
  // Provider registry: which provider is active (masked) + count.
  active_provider?: AIProviderConfig | null;
  providers_count?: number;
  // QuestLog (Idea 95): AI response cache status.
  cache?: {
    size: number;
    hits: number;
    misses: number;
    enabled: boolean;
    ttl_seconds: number;
  };
  // Phase 2 (Idea 11): embeddings capability.
  embeddings?: {
    available: boolean;
    model: string | null;
    dim: number;
    batch_size: number;
    backend: string;
  };
}

export interface AIInsightsStats {
  user: { level: number | null; total_xp: number; streak: number };
  tasks: {
    total: number;
    completed: number;
    completion_rate: number;
    recent_completions: { title: string; subject: string | null; due_date: string | null }[];
  };
  assignments: { pending: number; upcoming: { title: string; due_date: string; status: string }[] };
  exams: { upcoming_exams: { title: string; date: string }[] };
  habits: { total: number; active_streaks: number; best_streak: number };
}

export interface AIInsightsResponse {
  insights: string;
  stats: AIInsightsStats;
  cached: boolean;
  ai_used: boolean;
  // When the persisted insight snapshot was generated (present on both
  // cached loads and fresh computes) — lets the UI show "last updated".
  analyzed_at?: string | null;
}

export interface AIClientModels {
  models: string[];
  enabled: boolean;
  // Provider registry extras (backwards-compatible).
  active_provider?: AIProviderConfig | null;
  providers?: AIProviderConfig[];
}

export interface AICompleteRequest {
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  model?: string | null;
}

export interface AICompleteResponse {
  text: string;
  ai_used: boolean;
}

export interface AIQuizQuestion {
  q: string;
  opts: string[];
  ans: number;
}

export interface AIQuizResponse {
  questions: AIQuizQuestion[];
  ai_used: boolean;
}

export interface AIFlashcard {
  front: string;
  back: string;
}

export interface AIFlashcardsResponse {
  cards: AIFlashcard[];
  ai_used: boolean;
}

export interface AIStudyPlanWeek {
  week: number;
  topic: string;
  tasks: string[];
}

export interface AIStudyPlan {
  subject: string;
  exam_date: string | null;
  weeks: AIStudyPlanWeek[];
}

export interface AIStudyPlanResponse {
  plan: AIStudyPlan;
  ai_used: boolean;
}

export interface AISyllabusAssignment {
  title: string;
  due_date: string;
  course: string;
  priority: string;
}

export interface AISyllabusResponse {
  assignments: AISyllabusAssignment[];
  ai_used: boolean;
}

export interface AIGradeAnswerResponse {
  correct: boolean;
  explanation: string;
  ai_used: boolean;
}

export interface AIChatResponse {
  message: string;
  should_generate_plan?: boolean;
  plan_context?: unknown;
}
