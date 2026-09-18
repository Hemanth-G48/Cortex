// AI Tutor, practice, mocks, interview, skills types (Phase 7).
// Extracted from services/api.ts (F8 split).

// ----- Second Brain Phase 7 types (AI Tutor & Assessment, Ideas 61-70) -----
export interface TutorSource {
  chunk_id: number | null;
  document_id: number | null;
  title: string | null;
  source_path: string | null;
  snippet: string;
  score: number | null;
}

export interface TutorChatResponse {
  session_id: number;
  answer: string;
  sources: TutorSource[];
  empty_retrieval: boolean;
  ai_used: boolean;
}

export interface BlockingConcept {
  concept: string;
  definition: string | null;
  topic_id: number | null;
  topic_name: string | null;
  kind: string;
}

export interface TutorDoubtResponse extends TutorChatResponse {
  blocking_concepts: BlockingConcept[];
  follow_ups: string[];
}

export interface TutorSessionItem {
  id: number;
  created_at: string | null;
}

export interface PracticeQuestionItem {
  id: number;
  topic_id: number;
  topic_name: string | null;
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  bloom_level: string;
  difficulty: string;
  status: string;
  created_at: string | null;
}

export interface PracticeGenerateResponse {
  items: PracticeQuestionItem[];
  generated: number;
  deduped_skipped: boolean;
}

export interface AdaptiveSession {
  topic_id: number;
  tier: string;
  reason: string;
  available_tiers: string[];
  streak: number;
}

export interface PracticeSessionResponse {
  session: AdaptiveSession;
  question: PracticeQuestionItem | null;
}

export interface PracticeAnswerResponse {
  topic_id: number;
  tier: string;
  streak: number;
  tier_moved: boolean;
  accuracy_at_tier: number;
}

export interface MistakeAnalysisResponse {
  analysis_id: number;
  divergence: string;
  missed_points: string[];
  recommendation: string;
  recommended_chunk_id: number | null;
  recommended_concept_id: number | null;
  concept_definition: string | null;
  revision_task_created: boolean;
  ai_used: boolean;
}

export interface MockSection {
  title: string;
  question_ids: number[];
}

export interface MockTestItem {
  id: number;
  subject_id: number;
  title: string;
  duration_mins: number;
  status: string;
  sections: MockSection[];
  question_count: number;
  // Exam-run surface: answers + explanations are stripped server-side.
  questions?: MockQuestionItem[];
  created_at: string | null;
  /** Server-computed attempt count for this paper (defect #75). */
  attempt_count?: number;
}

export interface MockQuestionItem {
  id: number;
  topic_id: number | null;
  question: string;
  options: string[];
  difficulty: string;
}

export interface MockAttemptItem {
  id: number;
  mock_test_id: number;
  started_at: string | null;
  finished_at: string | null;
  score: number;
  total: number;
  per_topic: Record<string, { correct: number; total: number }>;
}

export interface MockSubmitResponse {
  attempt_id: number;
  mock_test_id: number;
  score: number;
  total: number;
  percentage: number;
  late_submission: boolean;
  per_topic: Record<string, { correct: number; total: number }>;
}

export interface InterviewQuestion {
  question: string;
  topic_id: number | null;
  expected: string;
  model_solution: string;
}

export interface InterviewSession {
  id: number;
  skill: string;
  level: string;
  questions: InterviewQuestion[];
  answers: Record<string, { answer: string; score: number; strengths: string[]; misconceptions: string[]; action_items: string[] }>;
  total_score: number;
  status: string;
  created_at: string | null;
}

export interface InterviewAnswerResponse {
  index: number;
  score: number;
  strengths: string[];
  misconceptions: string[];
  action_items: string[];
  ai_used: boolean;
}

export interface InterviewFinishResponse {
  session_id: number;
  skill: string;
  level: string;
  answered: number;
  total_score: number;
  status: string;
}

export interface GradeAnswerAdvancedResponse {
  score: number;
  strengths: string[];
  misconceptions: string[];
  action_items: string[];
  ai_used: boolean;
  mode: string;
}

export interface UserSkillItem {
  skill_id: string;
  name: string;
  level: number;
  mastery: number;
  contributing_topics: { topic_id: number; topic_name: string; score: number }[];
  updated_at: string | null;
}

export interface SkillsResponse {
  skills: UserSkillItem[];
}

export interface SkillsExportResponse {
  format: string;
  content: string;
}
