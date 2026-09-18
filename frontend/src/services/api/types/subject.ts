// Subject Management Core types (Second Brain Phase 5).
// Extracted from services/api.ts (F8 split).

// ----- Second Brain Phase 5 types (Subject Management Core, Ideas 41-50) -----
export type SubjectProfileStatus = 'proposed' | 'confirmed' | 'rejected';

export interface SubjectParsedUnit {
  title: string;
  description: string | null;
  topics: { name: string; outcomes: string[] }[];
  deadlines: string[];
}

export interface SubjectParsed {
  title: string | null;
  semester: string | null;
  credits: number | null;
  grading: string | null;
  units: SubjectParsedUnit[];
}

export interface SubjectProfile {
  id: number;
  user_id: number;
  curriculum_subject_id: number | null;
  semester: string | null;
  status: SubjectProfileStatus;
  created_at: string | null;
  updated_at: string | null;
  parsed: SubjectParsed | null;
  topics_count: number;
  units_count: number;
  raw_syllabus_text?: string | null;
}

export type TopicStatus = 'pending' | 'confirmed' | 'merged' | 'rejected';

export interface TopicOutcome {
  text: string;
  status: 'pending' | 'done';
  completed_at: string | null;
}

export interface TopicItem {
  id: number;
  subject_id: number;
  unit_id: number | null;
  name: string;
  normalized_name: string;
  bloom_level: string | null;
  difficulty: string | null;
  difficulty_confidence: number | null;
  first_pass_mins: number | null;
  review_mins: number | null;
  mastery_mins: number | null;
  outcomes: TopicOutcome[];
  status: TopicStatus;
}

export interface UnitMatchCandidate {
  title: string;
  description: string | null;
  candidate_unit_id: number | null;
  candidate_title: string | null;
  score: number;
  match_type: 'name' | 'embedding' | 'none';
}

export interface DependencyGraphTopic {
  id: number;
  name: string;
  normalized_name: string;
  status: TopicStatus;
  unit_id: number | null;
}

export interface DependencyEdge {
  id: number;
  prereq_topic_id: number;
  postreq_topic_id: number;
  weight: number;
  provenance: string;
}

export interface DependencyGraph {
  subject_id: number;
  topics: DependencyGraphTopic[];
  edges: DependencyEdge[];
}

export interface RoadmapWeek {
  week: number;
  topic_ids: number[];
  topics: string[];
  est_mins: number;
}

export interface RoadmapItem {
  id: number;
  subject_id: number;
  version: number;
  status: string;
  plan: { weekly_budget_minutes: number; weeks: RoadmapWeek[] };
  created_at: string | null;
}

export interface TimeBudgetResponse {
  items: TopicItem[];
  pacing_multiplier: number;
  total_first_pass_mins: number;
  total_mins: number;
}

// ----- Second Brain Phase 8 types (Personalization & Learning Memory, Ideas 71-80) -----
export interface UserPreference {
  depth: 'overview' | 'deep_dive';
  examples_vs_theory: number;
  style: 'concise' | 'detailed';
  /** Pomodoro focus duration (defect #58 — preferred session length). */
  session_length_mins: number;
  /** Pomodoro break duration (defect #58). */
  pomodoro_break_mins: number;
  explanation_style: 'plain' | 'analogy' | 'formal';
  onboarding_completed: boolean;
  updated_at?: string | null;
}

export interface KbConceptGap {
  concept_id: number;
  concept: string;
  definition: string | null;
  score: number;
  evidence: {
    strength: number;
    exposure_count: number;
    quiz_errors: number;
    retrieval_misses: number;
  };
  sources: { document_id: number; title: string }[];
}
