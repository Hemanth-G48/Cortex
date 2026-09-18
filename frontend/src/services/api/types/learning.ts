// Learning Path Planner types.
// Extracted from services/api.ts (F8 split).

export type LearningTopicStatus = 'known' | 'partial' | 'unknown' | 'advanced_unknown';

export interface LearningTopic {
  name: string;
  status: LearningTopicStatus;
  resources: { resource_index: number; title: string }[];
  difficulty?: string | null;
  est_time?: string | null;
}

export interface LearningDependency {
  from: string;
  to: string;
  // provenance: "platform" (the site stated it) vs "ai" (inferred).
  source?: string;
  note?: string | null;
  from_url?: string | null;
  to_url?: string | null;
}

export interface LearningResource {
  title: string;
  platform: string | null;
  url: string | null;
  type: string;
  topics: string[];
  skills: string[];
  difficulty: string;
  prerequisites: string[];
  estimated_time: string;
  learning_objectives: string[];
  completion_requirement: string;
  related_resources?: string[];
  dependencies?: string[];
  // Honest crawl state of the underlying source resource (Layer 1).
  crawl_status?: string | null;
}

export interface LearningPhase {
  phase: number;
  title: string;
  tasks: {
    title: string;
    resource_index: number | null;
    topics: string[];
    description?: string | null;
    difficulty?: string | null;
    est_time?: string | null;
  }[];
}

export interface LearningTask {
  id: number;
  phase: number;
  phase_title: string | null;
  sort_order: number;
  title: string;
  description: string | null;
  resource_title: string | null;
  resource_url: string | null;
  resource_type: string | null;
  difficulty: string | null;
  est_time: string | null;
  topics: string[];
  skills: string[];
  prerequisites: string[];
  resource_id: number | null;
  path_id: number | null;
  source_crawled: boolean;
  done: boolean;
}

export interface LearningPlanDetail {
  id: number;
  goal: string;
  goal_key: string | null;
  description: string | null;
  status: string;
  engine: string;
  created_at: string | null;
  generated_at: string | null;
  resources: LearningResource[];
  topics: LearningTopic[];
  dependencies: LearningDependency[];
  overview: string;
  phases: LearningPhase[];
  tasks: LearningTask[];
  stats: { total_tasks: number; done_tasks: number; progress_percent: number; truncated?: boolean };
  next_task: LearningTask | null;
  // Layer-1 source hierarchy (the REAL platform structure — source of truth).
  source: LearningPlanSource;
  // Per-learning-path progress rolled up from task states.
  path_progress: LearningPathProgress[];
}

/** One task inside a scheduled study day (roadmap → study schedule). */
export interface LearningScheduleTask {
  task_id: number;
  phase: number;
  phase_title: string | null;
  title: string;
  est_time: string;
  minutes: number;
  resource_title: string | null;
  resource_url: string | null;
  resource_type: string | null;
  done: boolean;
}

/** One day of the roadmap-derived study schedule. */
export interface LearningScheduleDay {
  day: number;
  date: string;
  label: string;
  total_minutes: number;
  slots: string[];
  tasks: LearningScheduleTask[];
}

/**
 * Roadmap → day-by-day study schedule (built on an explicit user action;
 * reading it never calls the LLM). ``stale`` is recomputed on read from the
 * live task rows so the UI can suggest a manual regeneration.
 */
export interface LearningSchedule {
  plan_id: number;
  goal: string;
  mode: string;
  params: {
    daily_hours: number;
    modules_per_day: number;
    budget_minutes: number;
    time_slots: string[];
    instruction: string | null;
  };
  generated_at: string;
  engine: string;
  stale: boolean;
  note: string | null;
  stats: {
    days: number;
    total_minutes: number;
    total_hours: number;
    tasks_scheduled: number;
    done_tasks: number;
    remaining_tasks: number;
    estimated_end_date: string | null;
  };
  days: LearningScheduleDay[];
}

export interface LearningSourceResource {
  id: number;
  title: string;
  url: string | null;
  resource_type: string;
  difficulty: string | null;
  section: string | null;
  sort_order: number;
  crawl_status: string;
  status_code: number | null;
  error: string | null;
}

export interface LearningSourcePath {
  id: number;
  platform: string;
  title: string;
  description: string | null;
  difficulty: string | null;
  source_url: string;
  first_resource_url: string | null;
  resource_total: number | null;
  section_count: number | null;
  resource_count: number | null;
  crawl_status: string;
  status_code: number | null;
  error: string | null;
  resources: LearningSourceResource[];
}

export interface LearningCrawlReport {
  platform: string | null;
  source_url: string | null;
  paths_discovered: number;
  paths_crawled: number;
  paths_failed: number;
  resources_extracted: number;
  resources_with_url: number;
  resources_verified: number;
  resources_failed: number;
  statuses: Record<string, number>;
}

export interface PortswiggerSessionStatus {
  configured: boolean;
  authenticated: boolean;
  email: string | null;
  expires_at: string | null;
  last_login_at: string | null;
  has_cookies: boolean;
}

export interface LearningReverifyReport {
  paths_rechecked: number;
  resources_unlocked: number;
  resources_verified: number;
  resources_failed: number;
  statuses: Record<string, number>;
}

export interface LearningPlanSource {
  report: LearningCrawlReport;
  paths: LearningSourcePath[];
}

export interface LearningPathProgress {
  path_id: number;
  title: string;
  done_tasks: number;
  total_tasks: number;
  progress_percent: number;
}

export interface LearningPlanSummary {
  id: number;
  goal: string;
  goal_key: string | null;
  status: string;
  engine: string;
  created_at: string | null;
  generated_at: string | null;
  source: {
    platform: string | null;
    paths_discovered: number;
    paths_crawled: number;
    paths_failed: number;
    resources_extracted: number;
    resources_verified: number;
    resources_failed: number;
  };
}
