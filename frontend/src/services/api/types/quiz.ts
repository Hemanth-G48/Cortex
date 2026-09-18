// SyllabusAI quiz types.
// Extracted from services/api.ts (F8 split).

// ----- SyllabusAI quizzes -----
export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface Quiz {
  id: number;
  unit_id: number;
  questions: QuizQuestion[];
  difficulty: string;
  created_at?: string | null;
}

export interface QuizAttemptResultItem {
  question_index: number;
  selected: number | null;
  correct: boolean;
  correct_index: number;
  explanation: string;
}

export interface QuizAttemptResult {
  score: number;
  total: number;
  percentage: number;
  results: QuizAttemptResultItem[];
  // G13 (Phase 85): XP granted for a passing attempt (0 when none).
  xp_awarded?: number;
}

export interface QuizHistoryItem {
  id: number;
  quiz_id: number;
  answers: number[];
  score: number | null;
  total_questions: number | null;
  created_at?: string | null;
}

export interface QuizAnalytics {
  avg_score: number;
  best_score: number;
  total_attempts: number;
  per_unit: Record<number, number>;
}
