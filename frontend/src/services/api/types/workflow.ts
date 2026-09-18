// Today / Triage / Backup / Weekly Review / Focus / Health Audit / Micro-session types.
// Extracted from services/api.ts (F8 split).

import type { KbDailyNotes, KbDerivedGoal, KbDocumentStatus, KbGoalItem, KbMissingNoteSuggestion, KbOutdatedNote, KbQualityItem, KbRecommendItem, KbReflection } from './kb'
import type { LearningTask } from './learning'

export interface TodayReviewDue {
  schedule_id: number;
  topic_id: number;
  topic_name: string;
  subject_id: number | null;
  interval_days: number;
  ease: number;
  repetitions: number;
  due_date: string | null;
}

export interface TodayScheduleItem {
  id: number;
  time_range: string;
  activity: string;
  category: string;
  done: boolean;
}

export interface TodayDeadline {
  kind: 'assignment' | 'exam' | 'task';
  id: number;
  title: string;
  course_id?: number | null;
  due_date: string | null;
  status: string;
}

export interface TodayCapturedDoc {
  id: number;
  title: string;
  doc_type: string;
  char_count: number;
  quality_score: number | null;
}

export interface TodayPomodoro {
  id: number;
  duration_minutes: number | null;
  task_description: string | null;
  completed: boolean;
}

export interface TodayJournal {
  id: number;
  mood: string | null;
  content: string;
  tags: string | null;
}

export interface TodayOverview {
  date: string;
  day_name: string;
  morning: {
    reviews_due: TodayReviewDue[];
    next_actions: KbRecommendItem[];
    schedule: TodayScheduleItem[];
    deadlines: TodayDeadline[];
    captured_documents: TodayCapturedDoc[];
  };
  evening: {
    focus_minutes: number;
    pomodoros: TodayPomodoro[];
    journal: TodayJournal[];
    daily: KbDailyNotes;
  };
  captured_today_count: number;
}

export interface TriageCategorizeProposal {
  id: number;
  proposed_path: string;
  rule: string;
}

export interface TriageItem {
  id: number;
  title: string;
  path_rel: string | null;
  doc_type: string;
  status: KbDocumentStatus;
  char_count: number;
  quality_score: number | null;
  created_at: string | null;
  detected_subjects: string[];
  tags: string[];
  categorize: TriageCategorizeProposal | null;
}

export interface TriageStats {
  pending: number;
  total_in_window: number;
  triaged: number;
  window_days: number;
}

export interface TriageQueueResponse {
  items: TriageItem[];
  stats: TriageStats;
}

export interface TriageBulkResult {
  ok: boolean;
  // accept-all
  processed?: number;
  accepted?: number;
  skipped_no_subjects?: number;
  subjects_applied?: number;
  // dismiss-all
  dismissed?: number;
  // shared
  remaining_pending: number;
}

export interface BackupRestoreResult {
  ok: boolean;
  restored_files: number;
  sources_matched: number;
  database_restored: boolean;
  database_skipped: boolean;
  warnings: string[];
  user_id?: number | null;
  exported_at?: string | null;
}

/** One micro-session tied to a learning-plan task (Study-Session Loop). */
export interface PlanSessionItem {
  id: number;
  learning_plan_id: number | null;
  learning_task_id: number | null;
  practice_task: string | null;
  duration_mins: number;
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

/** Read-only Study-Session Loop state for one plan. */
export interface PlanSessionState {
  plan_id: number;
  live_session: PlanSessionItem | null;
  last_session: PlanSessionItem | null;
  next_task: LearningTask | null;
  progress: { total_tasks: number; done_tasks: number; progress_percent: number };
  completed: boolean;
}

/** Plan Re-sync report (explicit action — refreshes Layer 1 only). */
export interface PlanResyncReport {
  resynced_at: string;
  urls_checked: number;
  paths_added: { id: number; title: string; source_url: string }[];
  paths_refreshed: number;
  paths_removed: { id: number; title: string; source_url: string }[];
  paths_failed: number;
  resources_extracted: number;
  errors: string[];
}

/** One near-duplicate pair with titles (Vault Health Audit). */
export interface HealthAuditDuplicate {
  document_id: number;
  duplicate_of_id: number;
  similarity: number;
  method: string;
  title: string | null;
  duplicate_of_title: string | null;
}

/** Vault Health Audit — read-only aggregate of existing signals. */
export interface HealthAudit {
  health: {
    score: number | null;
    document_count: number | null;
    edge_count: number | null;
    dead_links: number;
    orphans: number;
    stale_notes: number;
    unindexed_files: number;
  };
  sections: {
    missing_notes: KbMissingNoteSuggestion[];
    outdated_notes: KbOutdatedNote[];
    duplicates: HealthAuditDuplicate[];
    low_quality: KbQualityItem[];
  };
  counts: {
    missing_notes: number;
    outdated_notes: number;
    duplicates: number;
    low_quality: number;
  };
  scanned_at: string | null;
}

/** One subject readiness row (Focus/Readiness Loop). */
export interface FocusSubject {
  subject_id: number;
  forecast: number;
  readiness: number;
  at_risk: boolean;
  risk_threshold: number | null;
  exam_days_until: number | null;
  series_points: number;
  model: string;
}

/** Focus/Readiness Loop board — read-only, exam-aware. */
export interface FocusBoard {
  subjects: FocusSubject[];
  recommendations: (KbRecommendItem & { subject_readiness?: FocusSubject | null })[];
  at_risk_count: number;
  exam_approaching: FocusSubject[];
  total_subjects: number;
}

export interface WeeklyReviewCapture {
  id: number;
  title: string;
  doc_type: string;
  quality_score: number | null;
}

export interface WeeklyReviewWeakTopic {
  topic_id: number;
  topic_name: string;
  subject_id: number | null;
  score: number;
  classification: string;
}

export interface WeeklyQuest {
  id: number;
  title: string;
  description: string | null;
  xp_reward: number;
  status: string;
  due_date: string | null;
}

export interface WeeklyReviewResponse {
  week_start: string;
  week_end: string;
  week_label: string;
  activity: {
    captures: WeeklyReviewCapture[];
    captures_count: number;
    sessions_done: number;
    learning_events: number;
    focus_minutes: number;
    pomodoro_count: number;
  };
  reflection: KbReflection | null;
  goals: KbGoalItem[];
  derived_goals: KbDerivedGoal[];
  weak_topics: WeeklyReviewWeakTopic[];
  weekly_quests: WeeklyQuest[];
  week_start_monday: string;
}

export interface WeeklyReflectionResult {
  reflection: KbReflection;
  week_start: string;
}

// ----- Micro-session types (Idea 60 — launched from Today's next actions) -----
export interface MicroSession {
  id: number;
  topic_id: number | null;
  topic_name: string | null;
  chunk_id: number | null;
  practice_task: string | null;
  duration_mins: number | null;
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

export interface SessionPomodoroResult {
  ok: boolean;
  pomodoro_id: number;
  duration_minutes: number;
  task_description: string;
}
