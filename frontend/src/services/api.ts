import { toIso } from '../utils/vaultDates';

const BASE = '/api';

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts?.headers as Record<string, string> || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...opts,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data !== undefined && data !== null ? JSON.stringify(data) : undefined }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PATCH', body: data !== undefined && data !== null ? JSON.stringify(data) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/**
 * Download a backend file that requires the Authorization header (e.g.
 * BibTeX / mind-map exports) as a browser download.
 */
export async function downloadAsFile(url: string, filename: string): Promise<void> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ----- Auth types -----
export type UserRole = 'student' | 'teacher';

export interface User {
  id: number;
  name: string;
  avatar: string | null;
  avatar_class: string | null;
  current_level: number;
  current_streak: number;
  total_xp: number;
  created_at: string;
  // Fitness Hub (Phases 1-2)
  current_weight: number | null;
  initial_weight: number | null;
  target_weight: number | null;
  membership_status: string | null;
  next_payment_date: string | null;
  // Auth (Phase 3)
  username?: string | null;
  email?: string | null;
  role?: UserRole;
  // SyllabusAI (G1): local curator/admin flag.
  is_admin?: boolean;
  // SyllabusAI (G2): curriculum enrollment binding.
  institution_id?: number | null;
  program_id?: number | null;
}

export interface AuthUser extends User {
  role: UserRole;
  token: string;
}

// ----- Token helpers -----
export function getToken(): string | null {
  return localStorage.getItem('student_os_token');
}

export function setToken(t: string): void {
  localStorage.setItem('student_os_token', t);
}

export function clearToken(): void {
  localStorage.removeItem('student_os_token');
}

// ----- Auth API -----
export const authApi = {
  signup: (d: { name: string; username?: string; email?: string; password: string; role: UserRole; teacher_secret?: string }) =>
    request<{ user: AuthUser; token: string }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(d),
    }),
  login: (d?: { identifier?: string; password?: string }) =>
    request<{ user: AuthUser; token: string }>('/auth/login', {
      method: 'POST',
      body: d !== undefined ? JSON.stringify(d) : undefined,
    }).then((r) => {
      setToken(r.token);
      return r;
    }),
  me: () => request<{ user: AuthUser }>('/auth/me'),
  logout: () =>
    request<{ ok: boolean }>('/auth/logout', { method: 'POST' }).then(() => {
      clearToken();
      return { ok: true } as const;
    }),
};

// ----- Upload API -----
export const uploadApi = {
  upload: (file: File, kind?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (kind) formData.append('kind', kind);
    return fetch(`${BASE}/uploads`, {
      method: 'POST',
      body: formData,
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload ${res.status}: ${res.statusText}`);
      return res.json();
    }) as Promise<{ url: string; filename: string; size: number; content_type: string }>;
  },
};

export interface Course {
  id: number; title: string; image_url: string | null;
  current_assignment: number; total_assignments: number;
  next_exam: number | null; total_exams: number;
  status: string; user_id: number;
  credits: number;
  // SyllabusAI G12 (Phase 78): optional link to a catalog subject.
  curriculum_subject_id?: number | null;
}

export interface Task {
  id: number; title: string; subject_tag: string | null;
  priority_tag: string | null; priority_quadrant: string | null;
  due_date: string | null;
  status: string; user_id: number; project_id: number | null;
}

export interface Assignment {
  id: number; title: string; description: string | null;
  course_id: number; due_date: string; status: string;
  type?: string | null;
  type_color?: string | null;
  time_estimate?: number | null;
  file_url?: string | null;
}

export interface Exam {
  id: number; title: string; course_id: number;
  date: string; status: string;
}

export interface Note {
  id: number; title: string; content: string | null;
  course_id: number; created_date: string;
  pinned: boolean;
  updated_at: string | null;
}

export interface Goal {
  id: number; title: string; quarter: string;
  progress_percentage: number; year: number;
  habit_id: number | null; target_date: string | null;
  is_completed: boolean;
}

export interface Reminder {
  id: number; title: string; time: string | null;
  date: string; is_completed: boolean;
}

export interface Habit {
  id: number; name: string; description: string | null;
  frequency: string; target_count: number;
  current_streak: number; longest_streak: number; user_id: number;
  color_theme: string; is_archived: boolean;
  // Gamified Habit Tracker (Phases 1-3)
  habit_type: string; xp_reward: number; xp_penalty: number;
  image_url: string | null; days_caught: number;
  // Fitness Hub (Phase 3)
  goal: string | null; heatmap_data: string | null;
}

export interface HabitLog {
  id: number; habit_id: number; date: string;
  completed: boolean; count: number;
  // Gamified Habit Tracker (Phase 4)
  type: string; status: string; xp_change: number;
  // Phase 91: drag-and-drop sort within a calendar day column
  sort_order: number;
}

export interface HabitTodayItem {
  id: number; name: string; habit_type: string;
  xp_reward: number; xp_penalty: number; image_url: string | null;
  current_streak: number; days_caught: number;
  log_today: boolean; xp_today: number; status: string | null;
}

export interface HabitCalendarLog {
  id: number; habit_id: number; habit_name: string;
  habit_type: string; status: string; xp_change: number;
  count: number; completed: boolean; sort_order: number;
}

export interface HabitCalendarDay {
  date: string;
  logs: HabitCalendarLog[];
}

export interface HabitStats {
  records_this_month: number;
  days_missed: number;
  days_in_month: number;
  is_new_record: boolean;
  streak_graph: { date: string; streak_length: number }[];
}

export interface HabitHeatmapDay {
  date: string;
  completed: boolean;
  count: number;
}

export interface HabitHeatmap {
  month: string;
  days: HabitHeatmapDay[];
}

export interface PomodoroSession {
  id: number; user_id: number; start_time: string;
  duration_minutes: number; completed: boolean; task_description: string | null;
  // Gamified Habit Tracker (Phase 6)
  mode: string;
}

export interface Workout {
  id: number; user_id: number; date: string;
  type: string; duration_minutes: number;
  calories: number | null; notes: string | null;
}

export interface FitnessGoal {
  id: number; user_id: number; name: string;
  target: number; current: number; unit: string | null;
}

// ----- Fitness Hub types (99-phase plan, Phases 43-48) -----
export interface Exercise {
  id: number; name: string; muscle_group_id: number | null;
  sets: number; reps: number; weight: number; user_id: number;
}

export interface MuscleGroup {
  id: number; name: string; body_part: string;
  image_3d_url: string | null; sort_order: number; user_id: number;
}

export interface MuscleGroupOverview extends MuscleGroup {
  exercise_count: number;
}

export interface WorkoutSplit {
  id: number; day_of_week: number; split_name: string;
  exercise_list: string | null; week_number: number; user_id: number;
}

export interface SplitDay {
  day: string; day_of_week: number;
  split_name: string; exercises: string[];
}

export interface Expense {
  id: number; title: string; cost: number;
  date: string; category: string; user_id: number;
}

export interface ExpenseSummary {
  total: number;
  by_category: Record<string, number>;
}

export interface PersonalRecord {
  id: number; exercise_name: string;
  current_weight: number; target_weight: number;
  unit: string; user_id: number;
  // computed by pr_summary helper
  percent?: number;
}

export interface DietPlan {
  id: number; title: string; is_active: boolean;
  sort_order: number; user_id: number;
}

export interface WeightGoal {
  initial: number | null; current: number | null;
  target: number | null; percent: number;
}

export interface Membership {
  membership_status: string;
  next_payment_date: string | null;
  days_to_payment: number | null;
}

export interface SpecHabitHeatmap {
  id: number; name: string; goal: string | null;
  days_completed: number; percent: number;
  heatmap_7x7: { date: string; completed: boolean; count: number }[];
}

export interface FitnessHubSummary {
  weight_goal: WeightGoal | null;
  pr_tracker: PersonalRecord[];
  membership: Membership | null;
  diet_plans: DietPlan[];
  expenses_summary: ExpenseSummary;
  weekly_split: { 1: SplitDay[]; 2: SplitDay[] };
  muscle_groups: MuscleGroupOverview[];
  spec_habits: SpecHabitHeatmap[];
}

export interface JournalEntry {
  id: number; user_id: number; date: string;
  content: string; mood: string | null; tags: string | null;
}

export interface Quest {
  id: number; user_id: number; title: string;
  description: string | null; xp_reward: number;
  status: string; due_date: string | null;
  category: string | null; priority: string;
  time_estimate: number | null;
  created_at: string | null; updated_at: string | null;
}

export interface QuestTask {
  id: number; quest_id: number; title: string; completed: boolean;
}

export interface Project {
  id: number; user_id: number; name: string;
  description: string | null; status: string; deadline: string | null;
}

export interface ProjectTask {
  id: number; project_id: number; title: string; completed: boolean;
}

export interface ProjectSummary {
  total_tasks: number;
  incomplete_tasks: number;
  days_to_go: number | null;
  deadline_status: string;
}

export interface WeekStreak {
  habit: string;
  streak: number;
}

export interface VaultSummary {
  overdue_tasks: number;
  overdue_last_week: number;
  completed_today: number;
  total_habits: number;
  active_habits: number;
  current_week_streaks: WeekStreak[];
}

export interface CalendarTask {
  id: number; title: string; subject_tag: string | null;
  priority_tag: string | null; status: string; project_id: number | null;
}

export interface CalendarEvent {
  id: number; title: string;
  start_time: string | null; end_time: string | null;
  reference_type: string | null; color: string | null;
}

export interface CalendarDeadline {
  id: number; name: string; status: string;
}

export interface CalendarDay {
  date: string;
  day_of_week: number;
  label: string;
  tasks: CalendarTask[];
  schedule: CalendarEvent[];
  deadlines: CalendarDeadline[];
}

export interface VaultCalendar {
  start: string;
  end: string;
  days: CalendarDay[];
}

export interface DatabaseCounts {
  users: number;
  habits: number;
  tasks: number;
  projects: number;
  goals: number;
  logs: number;
  [key: string]: number;
}

// ----- Second Brain / Knowledge Base types (Phase 1) -----
export type KbSourceType = 'vault_folder' | 'local_dir' | 'upload' | 'cloud';

export type KbSyncType = 'none' | 'git' | 'drive' | 'clip';

export interface KbSource {
  id: number;
  user_id: number;
  name: string;
  source_type: KbSourceType;
  root_path: string | null;
  enabled: boolean;
  last_scanned_at: string | null;
  files_seen: number;
  files_added: number;
  files_changed: number;
  files_removed: number;
  created_at: string | null;
  document_count: number;
  // Phase 9 (Idea 89): external sync adapter + per-source cursor.
  sync_type: KbSyncType;
  sync_cursor: Record<string, unknown> | null;
}

export type KbDocumentStatus = 'new' | 'changed' | 'unchanged' | 'deleted' | 'failed' | 'draft';

export interface KbDocument {
  id: number;
  user_id: number;
  source_id: number | null;
  path_rel: string | null;
  title: string | null;
  doc_type: string;
  content_hash: string | null;
  char_count: number;
  frontmatter: Record<string, unknown> | null;
  outline: { level: number; text: string; char_start: number }[] | null;
  metadata: {
    wikilinks?: string[];
    tags?: string[];
    callouts?: string[];
    arxiv_id?: string;
    authors?: string[];
    abstract?: string;
  } | null;
  ocr_used: boolean;
  needs_ocr: boolean;
  status: KbDocumentStatus;
  doc_date: string | null;
  // Phase 2 metadata fields (Idea 13)
  author: string | null;
  source_url: string | null;
  language: string | null;
  reading_time_seconds: number | null;
  // Phase 2 dirty flags (Idea 20)
  embedding_dirty: boolean;
  graph_dirty: boolean;
  tags_dirty: boolean;
  // Phase 4 note-quality cache (Idea 39)
  quality_score: number | null;
  quality_detail: Record<string, unknown> | null;
  // Phase 9 (Idea 86): summary stale flag consumed by the nightly job.
  summary_dirty: boolean;
  created_at: string | null;
  updated_at: string | null;
  indexed_at: string | null;
  chunk_count: number;
}

export interface KbChunk {
  id: number;
  document_id: number;
  seq: number;
  content: string;
  char_start: number;
  char_end: number;
  heading_path: string | null;
  token_estimate: number;
}

export type KbJobStatus = 'queued' | 'running' | 'done' | 'failed' | 'interrupted';

export interface KbJob {
  id: number;
  user_id: number;
  job_type: string;
  status: KbJobStatus;
  total_items: number;
  processed_items: number;
  error: string | null;
  ref_type: string | null;
  ref_id: number | null;
  created_at: string | null;
  finished_at: string | null;
  summary: Record<string, number> | null;
}

export interface KbScanResult {
  job: KbJob;
  summary: Record<string, number> | null;
}

export interface KbDocumentListResponse {
  items: KbDocument[];
  total: number;
  page: number;
  page_size: number;
}

export interface KbUploadResult {
  document: KbDocument | null;
  deduped: boolean;
  duplicate_of_id: number | null;
}

export interface KbVersion {
  id: number;
  document_id: number;
  version_seq: number;
  content_hash: string | null;
  snapshot_text: string | null;
  created_at: string | null;
}

export interface KbDiffResponse {
  from_version: number;
  to_version: number;
  changed: boolean;
  diff: string;
}

// ----- Second Brain Phase 2 types (Embeddings, Indexing & Knowledge Graph) -----
export interface KbStats {
  document_count: number;
  chunk_count: number;
  embedding_count: number;
  embedded_documents: number;
  tag_count: number;
  concept_count: number;
  edge_count: number;
  duplicate_count: number;
  total_tokens: number;
  embeddings_today: number;
  embeddings_limit: number;
  inferences_today: number;
  inference_limit: number;
  dirty_documents: number;
}

export interface KbRelatedItem {
  id: number;
  title: string;
  relation: string | null;
  weight: number | null;
  provenance?: string | null;
  direction?: string | null;
}

export interface KbRelatedResponse {
  document_id: number;
  related: KbRelatedItem[];
  method: string;
}

export interface KbTagSuggestion {
  tag_id: number;
  name: string;
  provenance: string;
  confidence: number;
}

export interface KbDocumentTagsResponse {
  document_id: number;
  tags: KbTagSuggestion[];
}

export interface KbConcept {
  id: number;
  canonical_name: string;
  definition: string | null;
  aliases: string[] | null;
  document_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface KbDuplicateItem {
  document_id: number;
  duplicate_of_id: number;
  similarity: number;
  method: string;
  created_at: string | null;
}

export interface KbDuplicatesResponse {
  items: KbDuplicateItem[];
  total: number;
  method: string;
}

export interface KbMetadataUpdate {
  author?: string | null;
  source_url?: string | null;
  language?: string | null;
  reading_time_seconds?: number | null;
  metadata?: Record<string, unknown> | null;
}

// ----- Knowledge Graph types (Group 8, Phase 2) -----
export type KbGraphNodeKind = 'document' | 'concept' | 'tag';

export interface KbGraphNode {
  id: string;
  kind: KbGraphNodeKind;
  label: string;
  doc_type?: string | null;
  status?: string | null;
  degree: number;
}

export interface KbGraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  provenance: string;
}

export interface KbGraphResponse {
  nodes: KbGraphNode[];
  edges: KbGraphEdge[];
  truncated: boolean;
  total_nodes: number;
  total_edges: number;
}

// ----- Second Brain Phase 3 types (Search & Retrieval, Ideas 21-30) -----
export type KbSearchMode = 'keyword' | 'semantic' | 'hybrid';

export interface KbSearchItem {
  chunk_id: number;
  document_id: number;
  seq: number;
  title: string;
  snippet: string;
  score: number;
  mode: string;
  source_path: string | null;
  heading_path: string | null;
  doc_type: string;
  doc_date: string | null;
  char_start: number;
  char_end: number;
  sources: string[] | null;
}

export interface KbSearchResponse {
  items: KbSearchItem[];
  total: number;
  page: number;
  page_size: number;
  mode: string;
  original_query: string;
  expanded_query: string;
}

export interface KbSearchEventItem {
  id: number;
  query: string;
  mode: string;
  clicked_id: number | null;
  rating: number | null;
  created_at: string | null;
}

export interface KbHealth {
  score: number;
  document_count: number;
  edge_count: number;
  signals: {
    orphans: { count: number; document_ids: number[] };
    dead_links: {
      count: number;
      edges: {
        edge_id: number;
        source_document_id: number | null;
        target_document_id: number | null;
        relation: string;
      }[];
    };
    stale_notes: { count: number; document_ids: number[] };
    unindexed_files: {
      count: number;
      documents: { document_id: number; missing: string[] }[];
    };
    coverage_gaps: { topic: string; covered: number; coverage: number }[];
    // Phase 4 (Idea 39, phrase 90)
    avg_quality?: { average: number; weight: number };
  };
}

export interface KbGapItem {
  topic: string;
  coverage: number;
  is_gap: boolean;
}

export interface KbGapsResponse {
  items: KbGapItem[];
  gaps: KbGapItem[];
  threshold: number;
  total: number;
}

// ----- Second Brain Phase 4 types (Note Intelligence & Content Generation, Ideas 31-40) -----
export interface KbSummaryResponse {
  document_id: number;
  cached: boolean;
  summary: {
    content: string;
    key_points: string[];
    definitions: { term: string; definition: string }[];
    open_questions: string[];
  };
}

export interface KbExplainCitation {
  chunk_id: number;
  document_id: number | null;
  title: string | null;
  snippet: string;
  source_path: string | null;
  heading_path: string | null;
}

export interface KbExplainResponse {
  concept: string;
  depth: string;
  explanation: string;
  citations: KbExplainCitation[];
  fallback: boolean;
  document_ids: number[];
}

export interface KbFlashcardCandidate {
  id: number;
  document_id: number;
  document_title?: string;
  question: string;
  answer: string;
  source_chunk_id: number | null;
  status: string;
  // Phase 9 (Idea 85): manual | auto
  source?: string;
  created_at?: string | null;
}

export interface KbFlashcardGenerateResult {
  document_id: number;
  generated: number;
  skipped_duplicates: number;
  fallback: boolean;
  candidates: KbFlashcardCandidate[];
}

export interface KbCitation {
  id: number;
  document_id: number | null;
  cite_key: string;
  title: string | null;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  arxiv_id: string | null;
  raw_text: string | null;
  created_at?: string | null;
}

export interface KbMindMapNode {
  id: string;
  label: string;
  children: KbMindMapNode[];
  concepts: string[];
  chunk_ids: number[];
}

export interface KbDailyNoteDoc {
  id: number;
  title: string;
  doc_type: string;
  char_count: number;
  reading_time_seconds: number | null;
  quality_score: number | null;
}

export interface KbDailyNoteSchedule {
  id: number;
  time_range: string;
  activity: string;
  category: string;
  done: boolean;
}

export interface KbDailyNoteJournal {
  id: number;
  mood: string | null;
  content: string;
  tags: string | null;
}

export interface KbDailyNotes {
  date: string;
  documents: KbDailyNoteDoc[];
  schedule: KbDailyNoteSchedule[];
  journal: KbDailyNoteJournal[];
}

export interface KbQualitySuggestion {
  id: number;
  action: string;
  detail: string | null;
  status: string;
}

export interface KbQualityResult {
  document_id: number;
  score: number;
  components: Record<string, number>;
  weights: Record<string, number>;
  computed_at?: string;
  suggestions: KbQualitySuggestion[];
}

export interface KbQualityItem {
  document_id: number;
  title: string;
  doc_type: string;
  score: number;
  components: Record<string, number>;
  suggestions: number;
}

export interface KbLinksResponse {
  document_id: number;
  concepts: { concept_id: number; edge_id?: number; name: string; weight: number }[];
  related: { id: number; edge_id?: number; title: string; relation: string; weight: number }[];
}

export interface GlobalSearchHit {
  id: number;
  title: string;
  domain: string;
  snippet: string;
  url: string;
  score: number;
}

export interface GlobalSearchResponse {
  items: GlobalSearchHit[];
  groups: Record<string, GlobalSearchHit[]>;
  total: number;
  query: string;
  domains: string[];
}

export interface LifeArea {
  id: number; user_id: number; name: string;
  satisfaction_score: number; goal: string | null;
  description: string | null; image_url: string | null;
  progress_percent: number; sort_order: number;
  target_days: number | null; status: string;
  complete_in_days: number | null;
  // Gamified Habit Tracker (Phase 7)
  total_xp_earned: number;
}

export interface Character {
  id: number; user_id: number; name: string;
  class_name: string; level: number; xp: number;
  strength: number; agility: number; intelligence: number; endurance: number;
  current_quests: number; created_at: string | null; updated_at: string | null;
}

export interface AddXpRequest {
  amount: number;
}

export interface Reward {
  id: number; user_id: number; title: string;
  description: string | null; xp_cost: number; category: string;
  image_url: string | null; is_available: boolean; claimed_date: string | null; created_at: string | null;
}

export interface ClaimRewardResponse {
  reward_id: number; title: string; xp_cost: number; xp_remaining: number; claimed_at: string | null;
}

export interface Mission {
  id: number; user_id: number; title: string;
  description: string | null; mission_type: string | null;
  priority: string; status: string; due_date: string | null;
  xp_reward: number; linked_quests: string | null;
  created_at: string | null; updated_at: string | null;
}

export interface MissionTask {
  id: number; mission_id: number; title: string;
  completed: boolean; sort_order: number; created_at: string | null;
}

// ----- Quest Centre types (Gamified Quest Centre dashboard) -----
export interface GamificationProfile {
  id: number; name: string;
  avatar_class: string | null;
  current_streak: number;
  total_xp: number;
  current_level: number;
}

export interface StatusWindowCharacter {
  id: number; name: string;
  class_name: string; level: number; xp: number;
  avatar_class: string | null; current_streak: number;
}

export interface TodayTask {
  id: number; title: string; status: string;
  due_date: string | null; xp_reward: number;
}

export interface StatusWindow {
  character: StatusWindowCharacter | null;
  xp_to_next: number | null;
  today_tasks: TodayTask[];
}

export interface ProgressReport {
  year: number; month: number; week: number; day: number;
}

export interface PriorityWindowItem {
  title: string; time_estimate: number | null;
  id: number; kind: 'quest' | 'task';
}

export interface PriorityWindow {
  High: PriorityWindowItem[];
  Medium: PriorityWindowItem[];
  Low: PriorityWindowItem[];
}

export interface QuickAction {
  label: string; kind: string; route: string;
}

export interface QuickActionsResponse {
  actions: QuickAction[];
}

export interface CalendarQuest {
  id: number; title: string; status: string;
  priority: string | null; category: string | null; xp_reward: number;
}

export interface QuestDateGroup {
  date: string; quests: CalendarQuest[];
}

export interface QuestCentreCalendar {
  quests_by_date: QuestDateGroup[];
  schedule_events: ScheduleEvent[];
}

export interface QuestCentreLifeArea extends LifeArea {
  complete_in_days: number | null;
}

export interface ScheduleEvent {
  id: number; user_id: number; title: string;
  day_of_week: number; start_time: string | null; end_time: string | null;
  event_type: string | null; location: string | null;
  reference_type: string | null; reference_id: number | null;
  color: string | null; created_at: string | null;
}

// ----- Gamified Habit Tracker types (99-phase plan) -----
export interface HabitTrackerCharacter {
  id: number; name: string;
  class_name: string; level: number; xp: number;
  avatar_class: string | null; current_streak: number;
}

export interface HabitTrackerTodayStat {
  id: number; habit_id: number; habit_name: string;
  habit_type: string; status: string; xp_change: number;
}

export interface HabitTrackerStatusWindow {
  character: HabitTrackerCharacter | null;
  xp_to_next: number | null;
  today_habits: HabitTrackerTodayStat[];
}

export interface HabitTrackerLifeArea {
  id: number; name: string; goal: string | null;
  image_url: string | null; status: string;
  progress_percent: number; sort_order: number;
  total_xp_earned: number;
}

export interface HabitTrackerSummary {
  total_xp: number;
  level: number;
  current_streak: number;
  good_today: number;
  bad_today: number;
  xp_to_next: number;
  good_count: number;
  bad_count: number;
  life_areas: HabitTrackerLifeArea[];
  rewards_available: Reward[];
}

export interface DailyLog {
  id: number; user_id: number; date: string;
  time_focused: number; status: string;
}

export interface DailyLogStats {
  total_focused_minutes: number;
  days_active_this_month: number;
  days_in_month: number;
  today: { date: string; time_focused: number };
}

export interface LifePlannerEvent {
  id: number; user_id: number; title: string;
  time: string | null; date: string; location: string | null;
  is_completed: boolean;
}

export interface LifeAreaProgress {
  id: number; name: string; progress_percent: number;
}

export interface LifePlannerSummary {
  current_streak: number;
  longest_streak: number;
  daily_log_today: { date: string; time_focused: number; status: string };
  tasks_due_today: number;
  habits_active: number;
  goals_active: number;
  life_area_progress: LifeAreaProgress[];
}

export interface QuickTask {
  id: number;
  type: 'reminder' | 'task' | 'event';
  title: string;
  time: string | null;
  date: string | null;
  completed: boolean;
}

export interface EisenhowerTask {
  id: number; title: string; subject_tag: string | null;
  priority_tag: string | null; priority_quadrant: string | null;
  due_date: string | null; status: string;
}

export interface EisenhowerMatrix {
  urgent_important: EisenhowerTask[];
  important_not_urgent: EisenhowerTask[];
  urgent_not_important: EisenhowerTask[];
  not_important: EisenhowerTask[];
}

// ----- AI types (99-phase plan, Group 1) -----

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

// ----- Grades types (99-phase plan, Groups 2-3) -----
export interface Grade {
  id: number;
  course_id: number;
  assignment_id: number | null;
  title: string;
  points_earned: number;
  points_possible: number;
  category_id: number | null;
  date: string | null;
}

export interface CourseWeight {
  id: number;
  course_id: number;
  name: string;
  weight: number;
}

export interface GradeCalculateResult {
  course_id: number;
  percentage: number | null;
  letter_grade: string | null;
  is_weighted: boolean;
  total_earned: number | null;
  total_possible: number | null;
  grade_count: number;
}

export interface GPACourse {
  course_id: number;
  title: string;
  credits: number;
  percentage: number | null;
  letter_grade: string | null;
  gpa: number | null;
}

export interface GPAResponse {
  gpa: number | null;
  courses: GPACourse[];
}

export interface NeededOnFinalResponse {
  needed_pct: number;
}

// ----- Flashcards types (99-phase plan, Groups 4-5) -----
export interface Flashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: string;
  streak: number;
  next_review: string | null;
  created_at: string | null;
}

// FSRS spaced-repetition state (Idea 52 — vendored py-fsrs).
export interface FlashcardSchedule {
  card_id: number;
  next_review: string | null;
  interval_days: number;
  state: number | null;
  stability: number | null;
  fsrs_difficulty: number | null;
  reps: number;
  lapses: number;
  streak: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  name: string;
  username: string | null;
  avatar_class: string | null;
  level: number;
  current_streak: number;
  total_xp: number;
  me: boolean;
}

export interface LeaderboardMe {
  user_id: number;
  total_xp: number;
  rank: number;
  percentile: number;
  total_users: number;
}

export interface LeaderboardResponse {
  items: LeaderboardEntry[];
  me: LeaderboardMe;
}

export interface DueFlashcard {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  difficulty: string;
  next_review: string | null;
  interval_days: number;
  streak: number;
}

export interface FlashcardDeck {
  id: number;
  name: string;
  course_id: number | null;
  created_at: string | null;
  card_count: number;
  cards: Flashcard[];
}

// ----- Study plans types (99-phase plan, Groups 6-7) -----
export interface StudyPlanWeek {
  week: number;
  topic: string;
  tasks: string[];
}

export interface StudyPlan {
  id: number;
  subject: string;
  exam_date: string | null;
  weeks: StudyPlanWeek[];
  created_at: string | null;
}

// ----- Analytics types (99-phase plan, Groups 11-12) -----
export interface AnalyticsSummary {
  total_focus_minutes: number;
  weekly_focus_minutes: number;
  completed_assignments: number;
  total_assignments: number;
  completion_rate: number;
  gpa: number | null;
  total_xp: number;
  level: number;
  current_streak: number;
}

export interface WeeklyFocus {
  week: string;
  label: string;
  minutes: number;
}

export interface HeatmapDay {
  date: string;
  minutes: number;
}

// ----- Google sync types (99-phase plan, Group 14) -----
export interface GoogleStatus {
  connected: boolean;
  email: string | null;
  scopes: string[];
}

export interface GoogleConnectResponse {
  url: string | null;
  error?: string | null;
}

export interface ClassroomCourse {
  id: string;
  name: string;
  description: string | null;
}

export interface ClassroomAssignment {
  id: string;
  courseId: string;
  courseName: string;
  title: string;
  description: string;
  dueDate: string | null;
  status: string;
}

export interface GmailMessage {
  id: string;
  from: string;
  subject: string;
  date: string;
  snippet: string;
}

export interface GmailUnread {
  count: number;
}

export interface CalendarSyncEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location: string | null;
  link: string | null;
}

// ----- SyllabusAI curriculum types -----
export interface Institution {
  id: number;
  name: string;
  short_name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface Program {
  id: number;
  institution_id: number;
  name: string;
  code: string;
  description: string | null;
  duration: number;
  is_active: boolean;
  created_at?: string | null;
}

export interface Subject {
  id: number;
  program_id: number;
  name: string;
  code: string;
  semester: number | null;
  credits: number;
  description: string | null;
  is_active: boolean;
  unit_count: number;
  created_at?: string | null;
}

export interface CurriculumUnit {
  id: number;
  subject_id: number;
  unit_number: number;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at?: string | null;
}

// ----- SyllabusAI materials -----
export interface Material {
  id: number;
  unit_id: number;
  title: string;
  description: string | null;
  file_type: string;
  file_url: string;
  file_size: number;
  original_file_name: string;
  view_count: number;
  download_count: number;
  is_active: boolean;
  extracted_text: string | null;
  created_at: string;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
  page: number;
  page_size: number;
}

// ----- SyllabusAI summaries -----
export interface Summary {
  id: number;
  unit_ids: number[];
  content: string;
  key_points: string[];
  created_at?: string | null;
}

export interface SummaryGenerateResponse {
  summary: { content: string; key_points: string[] };
  cached: boolean;
}

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

// ----- SyllabusAI enrollment -----
export interface EnrollmentSummary {
  institution_id: number | null;
  program_id: number | null;
  institution_name: string | null;
  program_name: string | null;
  subjects: Subject[];
  units: CurriculumUnit[];
  material_count: number;
  quiz_attempts: number;
  avg_quiz_percentage: number | null;
  uploaded_materials: number;
}

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
  session_length_mins: number;
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

export interface KbMemoryItem {
  concept_id: number;
  concept: string;
  strength: number;
  exposure_count: number;
  last_seen: string | null;
  source: string;
}

export interface KbRecommendItem {
  topic_id: number;
  topic_name: string;
  subject_id: number;
  score: number;
  ready: boolean;
  blocked_by: number[];
  session_length_mins: number;
  reasons: Record<string, number>;
}

export interface KbConnectSuggestion {
  document_id: number;
  title: string;
  shared_concepts: string[];
  reasons: string[];
  target_status: string;
}

export interface KbConnectSuggestionsResponse {
  items: KbConnectSuggestion[];
  contradiction_hints: number[];
}

export interface KbMissingNoteSuggestion {
  id: number;
  concept_id: number | null;
  concept: string | number;
  reason: string;
  outline: string[];
  linked_material_ids: number[];
  status: 'suggested' | 'accepted' | 'dismissed';
}

export interface KbOutdatedNote {
  id: number;
  document_id: number;
  title: string;
  reason: 'contradiction' | 'stale' | 'material_changed';
  evidence: Record<string, unknown> | null;
  status: 'open' | 'updated' | 'archived' | 'dismissed';
  created_at: string | null;
}

export interface KbPersonalizedExplainResponse extends KbExplainResponse {
  anchors: string[];
  personalized: boolean;
}

export interface KbAdaptation {
  roadmap_id: number | null;
  version: number | null;
  status: string | null;
  topic_ids: number[];
  diff: {
    added_reviews: number;
    added_topic_ids: number[];
    removed_topics: number[];
    removed_topic_ids: number[];
    reordered: number[];
    reason: string;
    reasons: string[];
  };
}

// ----- Second Brain Phase 9 types (Automation, Ideas 81-90) -----
export interface KbAutomationJob {
  name: string;
  enabled: boolean;
  toggle: string;
  cap: number | null;
  budget_kind: string | null;
  description: string;
}

export interface KbAutomationRunResult {
  job?: string;
  job_id?: number;
  status?: string;
  skipped?: boolean;
  reason?: string;
  results?: { job: string; skipped?: boolean; reason?: string }[];
  count?: number;
}

export interface KbSourceSyncResult {
  source_id: number;
  sync_type?: string;
  changes?: number;
  imported?: number;
  unchanged?: number;
  skipped_stale?: number;
  failed?: number;
  skipped?: boolean;
  reason?: string;
}

export interface KbSourceSyncStatus {
  source_id: number;
  name: string;
  sync_type: string;
  last_scanned_at: string | null;
  cursor: Record<string, unknown>;
}

// ----- Second Brain Phase 10 types (Advanced AI, Analytics & Platform, Ideas 91-100) -----
export interface KbAgentStep {
  agent: string;
  status?: string;
  output?: Record<string, unknown>;
  error?: string | null;
  latency_ms?: number;
}

export interface KbAgentRun {
  id?: number;
  run_id?: number;
  request: string;
  status?: string;
  plan?: { agent: string; inputs: Record<string, unknown>; expected_output?: string; budget?: number }[];
  steps?: KbAgentStep[];
  result?: string | null;
  latency_ms?: number;
  cost_estimate?: number;
  created_at?: string | null;
}

export interface KbMemoryEpisode {
  id: number;
  event_type: string;
  summary: string;
  refs: Record<string, unknown> | null;
  created_at: string | null;
}

export interface KbMemoryTimeline {
  episodes: KbMemoryEpisode[];
  durable_facts: { concept: string; strength: number }[];
  total: number;
}

export interface KbContextBundle {
  active_subject: { subject_id: number | null; subject_name: string | null } | null;
  upcoming_exams: { exam_id: number; title: string; subject_id: number; days_until: number; date: string }[];
  recent_topics: { topic_id: number; topic_name: string; subject_id: number | null }[];
  question_history: { attempts_7d: number; avg_accuracy_7d: number | null };
  session_length_mins: number;
  memory: { concepts_known: number; anchors: number; concept_rows: number };
  override: Record<string, unknown>;
}

export interface KbResearchContribution {
  statement: string;
  novelty?: string;
  limitation?: string;
}

export interface KbRelatedPaper {
  document_id: number;
  title: string | null;
  doc_type: string;
  score: number;
  signals: { shared_concepts: number; title_overlap: number; shared_citations: number };
}

export interface KbResearchExplainResult {
  document_id: number;
  title: string | null;
  summary: { content: string; key_points: string[]; definitions: unknown[]; open_questions: string[] } | null;
  cached?: boolean;
  contributions: KbResearchContribution[];
  related: KbRelatedPaper[];
  synthesis: {
    answer: string;
    faithfulness_score: number;
    ai_used: boolean;
    citations: { chunk_id: number; document_id: number | null; title: string | null; source_path: string | null }[];
    grounded: boolean;
  } | null;
}

export type KbRecommendationDomain = 'study' | 'revisit' | 'read' | 'practice';

export interface KbRecommendationItem {
  id: string;
  domain: KbRecommendationDomain;
  target: number;
  title: string;
  reason: string;
  score: number;
  urgency: number;
  weakness: number;
  readiness: number;
}

export interface KbReflection {
  id: number;
  week_start: string;
  content: string;
  insights: { worked: string[]; struggled: string[]; change: string[]; insights: string[] };
  created_at: string | null;
  pushed?: boolean;
}

export interface KbDerivedGoal {
  subject_id: number;
  title: string;
  quarter: string;
  year: number;
  target_date: string;
  roadmap_id?: number | null;
}

export interface KbGoalItem {
  id: number;
  title: string;
  quarter: string;
  year: number;
  subject_id: number | null;
  roadmap_id: number | null;
  target_date: string | null;
  progress_percentage: number;
  is_completed: boolean;
}

export interface KbForecastPoint {
  date: string;
  value: number;
  events: number;
  ewma?: number;
}

export interface KbForecast {
  subject_id: number;
  points: KbForecastPoint[];
  model: string;
  forecast: number;
  readiness: number;
  at_risk: boolean;
  risk_threshold?: number;
  exam_days_until: number | null;
  series_points: number;
}

export interface KbObservabilityPayload {
  total: number;
  cost_estimate: number;
  tokens: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  feedback: { positive: number; negative: number; neutral: number };
  avg_faithfulness: number | null;
  by_feature: Record<string, { count: number; cost_estimate: number; avg_latency_ms: number; feedback: number }>;
  recent?: { id: number; feature: string; request: string | null; latency_ms: number; feedback: number; created_at: string | null }[];
}

export interface KbPromptVersion {
  id: number;
  feature: string;
  version: number;
  is_active: boolean;
  template: string;
  created_at: string | null;
}

// ----- API endpoint helpers -----
export const endpoints = {
  // LEGACY BOOT ONLY — no-body login returns the FIRST user and calls
  // setToken(), overwriting any logged-in user's token. Do NOT use this in
  // components; read the authenticated user from useAuth() instead.
  login: () => authApi.login().then((r) => ({ user: r.user })),
  curriculum: {
    institutions: () => api.get<Institution[]>('/curriculum/institutions'),
    institution: (id: number) => api.get<Institution>(`/curriculum/institutions/${id}`),
    programs: (institutionId: number) =>
      api.get<Program[]>(`/curriculum/institutions/${institutionId}/programs`),
    program: (id: number) => api.get<Program>(`/curriculum/programs/${id}`),
    subjects: (programId: number) =>
      api.get<Subject[]>(`/curriculum/programs/${programId}/subjects`),
    subject: (id: number) => api.get<Subject>(`/curriculum/subjects/${id}`),
    units: (subjectId: number) =>
      api.get<CurriculumUnit[]>(`/curriculum/subjects/${subjectId}/units`),
    unit: (id: number) => api.get<CurriculumUnit>(`/curriculum/units/${id}`),
  },
  materials: {
    list: (unitId: number, q?: string, page = 1, pageSize = 20) => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (q) params.set('q', q);
      return api.get<MaterialListResponse>(`/curriculum/units/${unitId}/materials?${params.toString()}`);
    },
    detail: (id: number) => api.get<Material>(`/materials/${id}`),
    upload: (unitId: number, file: File) => {
      const form = new FormData();
      form.append('file', file);
      return fetch(`${BASE}/curriculum/units/${unitId}/materials`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      }).then((res) => {
        if (!res.ok) throw new Error(`Upload ${res.status}: ${res.statusText}`);
        return res.json();
      }) as Promise<Material>;
    },
    downloadUrl: (id: number) => `${BASE}/materials/${id}/download`,
  },
  summaries: {
    generate: (unitIds: number[]) => api.post<SummaryGenerateResponse>('/summaries', { unit_ids: unitIds }),
    list: () => api.get<Summary[]>('/summaries'),
    remove: (id: number) => api.del<{ ok: boolean }>(`/summaries/${id}`),
  },
  quizzes: {
    generate: (unitId: number, numQuestions = 10, difficulty = 'medium') =>
      api.post<Quiz>('/quizzes', { unit_id: unitId, num_questions: numQuestions, difficulty }),
    attempt: (quizId: number, answers: (number | null)[]) =>
      api.post<QuizAttemptResult>(`/quizzes/${quizId}/attempt`, { answers }),
    history: () => api.get<QuizHistoryItem[]>('/quizzes/history'),
    analytics: () => api.get<QuizAnalytics>('/quizzes/analytics'),
  },
  enrollment: {
    summary: () => api.get<EnrollmentSummary>('/enrollment/summary'),
    update: (d: { institution_id: number; program_id: number }) =>
      api.put<{ user: AuthUser }>('/auth/enrollment', d),
  },
  admin: {
    allInstitutions: () => api.get<Institution[]>('/curriculum/institutions/admin/all'),
    createInstitution: (d: {
      name: string;
      short_name: string;
      description?: string | null;
      is_active?: boolean;
    }) => api.post<Institution>('/curriculum/institutions', d),
    toggleInstitution: (id: number) =>
      api.patch<{ ok: boolean; is_active: boolean }>(`/curriculum/institutions/${id}/status`),
    createProgram: (institutionId: number, d: { name: string; code: string; description?: string | null; duration?: number }) =>
      api.post<Program>(`/curriculum/institutions/${institutionId}/programs`, d),
    createSubject: (programId: number, d: {
      name: string;
      code: string;
      semester?: number | null;
      credits?: number;
      description?: string | null;
    }) => api.post<Subject>(`/curriculum/programs/${programId}/subjects`, d),
    createUnit: (subjectId: number, d: { unit_number: number; name: string; description?: string | null }) =>
      api.post<CurriculumUnit>(`/curriculum/subjects/${subjectId}/units`, d),
  },
  analytics: {
    summary: () => api.get<AnalyticsSummary>('/analytics/summary'),
    weeklyFocus: (weeks = 8) => api.get<WeeklyFocus[]>(`/analytics/weekly-focus?weeks=${weeks}`),
    heatmap: (weeks = 52) => api.get<HeatmapDay[]>(`/analytics/heatmap?weeks=${weeks}`),
  },
  google: {
    connect: () => api.get<GoogleConnectResponse>('/auth/google'),
    status: () => api.get<GoogleStatus>('/auth/google/status'),
    disconnect: () => api.post<{ connected: boolean }>('/auth/google/disconnect'),
  },
  classroom: {
    courses: () => api.get<ClassroomCourse[]>('/classroom/courses'),
    assignments: () => api.get<ClassroomAssignment[]>('/classroom/assignments'),
  },
  gmail: {
    unread: () => api.get<GmailUnread>('/gmail/unread'),
    messages: (limit = 10) => api.get<GmailMessage[]>(`/gmail/messages?limit=${limit}`),
  },
  calendarSync: {
    events: () => api.get<CalendarSyncEvent[]>('/calendar/events'),
  },
  studyPlans: {
    list: () => api.get<StudyPlan[]>('/study-plans'),
    get: (id: number) => api.get<StudyPlan>(`/study-plans/${id}`),
    create: (d: { subject: string; exam_date?: string | null; weeks: StudyPlanWeek[] }) =>
      api.post<StudyPlan>('/study-plans', d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/study-plans/${id}`),
  },
  flashcards: {
    list: () => api.get<FlashcardDeck[]>('/flashcard-decks'),
    get: (id: number) => api.get<FlashcardDeck>(`/flashcard-decks/${id}`),
    create: (d: { name: string; course_id?: number | null }) => api.post<FlashcardDeck>('/flashcard-decks', d),
    update: (id: number, d: Partial<FlashcardDeck>) => api.put<FlashcardDeck>(`/flashcard-decks/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/flashcard-decks/${id}`),
    cards: (deckId: number) => api.get<Flashcard[]>(`/flashcard-decks/${deckId}/cards`),
    addCard: (deckId: number, d: Partial<Flashcard>) => api.post<Flashcard>(`/flashcard-decks/${deckId}/cards`, d),
    updateCard: (deckId: number, cardId: number, d: Partial<Flashcard>) =>
      api.put<Flashcard>(`/flashcard-decks/${deckId}/cards/${cardId}`, d),
    deleteCard: (deckId: number, cardId: number) =>
      api.del<{ ok: boolean }>(`/flashcard-decks/${deckId}/cards/${cardId}`),
    // FSRS spaced repetition (Idea 52 — vendored py-fsrs).
    due: (deckId?: number) =>
      api.get<{ items: DueFlashcard[]; count: number }>(
        `/flashcard-decks/due${deckId ? `?deck_id=${deckId}` : ''}`,
      ),
    dueCounts: () => api.get<{ counts: Record<string, number> }>('/flashcard-decks/due-counts'),
    review: (deckId: number, cardId: number, grade: number) =>
      api.post<{ ok: boolean; schedule: FlashcardSchedule }>(
        `/flashcard-decks/${deckId}/cards/${cardId}/review`,
        { grade },
      ),
  },
  // Leaderboard (adapted from Shiori-v1 / QuestLog).
  leaderboard: {
    list: (limit = 20) => api.get<LeaderboardResponse>(`/leaderboard?limit=${limit}`),
  },
  grades: {
    list: () => api.get<Grade[]>('/grades'),
    byCourse: (cid: number) => api.get<Grade[]>(`/grades/courses/${cid}`),
    create: (d: Partial<Grade>) => api.post<Grade>('/grades', d),
    update: (id: number, d: Partial<Grade>) => api.put<Grade>(`/grades/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/grades/${id}`),
    calculate: (courseId: number) => api.post<GradeCalculateResult>('/grades/calculate', { course_id: courseId }),
    gpa: () => api.get<GPAResponse>('/grades/gpa'),
    neededOnFinal: (d: { current_pct: number; final_weight_pct: number; desired_pct: number }) =>
      api.post<NeededOnFinalResponse>('/grades/needed-on-final', d),
    weights: (cid: number) => api.get<CourseWeight[]>(`/grades/courses/${cid}/weights`),
    createWeight: (d: { course_id: number; name: string; weight: number }) => api.post<CourseWeight>('/grades/weights', d),
    updateWeight: (id: number, d: Partial<CourseWeight>) => api.put<CourseWeight>(`/grades/weights/${id}`, d),
    deleteWeight: (id: number) => api.del<{ ok: boolean }>(`/grades/weights/${id}`),
  },
  ai: {
    health: () => api.get<AIHealth>('/ai/health'),
    models: () => api.get<AIClientModels>('/ai/models'),
    complete: (d: Partial<AICompleteRequest>) => api.post<AICompleteResponse>('/ai/complete', d),
    quiz: (content?: string) => api.post<AIQuizResponse>('/ai/quiz', { content }),
    flashcards: (d: { content?: string; topic?: string; difficulty?: string }) =>
      api.post<AIFlashcardsResponse>('/ai/flashcards', d),
    studyPlan: (subject: string, examDate?: string) =>
      api.post<AIStudyPlanResponse>('/ai/study-plan', { subject, exam_date: examDate ?? null }),
    syllabus: (text: string) => api.post<AISyllabusResponse>('/ai/syllabus', { text }),
    gradeAnswer: (d: { question: string; expected: string; answer: string }) =>
      api.post<AIGradeAnswerResponse>('/ai/grade-answer', d),
    chat: (d: { message: string }) => api.post<AIChatResponse>('/ai/chat', d),
    // QuestLog (Idea 95): cached productivity insights from real user stats.
    insights: () => api.post<AIInsightsResponse>('/ai/insights'),
    // Local-first provider registry (configurable AI models).
    providers: {
      list: () => api.get<AIProvidersResponse>('/ai/providers'),
      create: (d: {
        name: string;
        provider_type: AIProviderType;
        base_url?: string | null;
        api_key?: string | null;
        model?: string | null;
        enabled?: boolean;
        is_default?: boolean;
      }) => api.post<AIProviderConfig>('/ai/providers', d),
      update: (
        id: string,
        d: {
          name?: string | null;
          provider_type?: AIProviderType | null;
          base_url?: string | null;
          api_key?: string | null; // empty/None → leave unchanged
          model?: string | null;
          enabled?: boolean | null;
          is_default?: boolean | null;
        },
      ) => api.put<AIProviderConfig>(`/ai/providers/${id}`, d),
      remove: (id: string) => api.del<{ ok: boolean }>(`/ai/providers/${id}`),
      test: (id: string) => api.post<AIProviderTestResult>(`/ai/providers/${id}/test`),
      refreshModels: (id: string) => api.post<AIProviderConfig>(`/ai/providers/${id}/refresh-models`),
      setDefault: (id: string) => api.post<AIProviderConfig>(`/ai/providers/${id}/default`),
    },
  },
  courses: {
    list: () => api.get<Course[]>('/courses/'),
    get: (id: number) => api.get<Course>(`/courses/${id}`),
    create: (d: Partial<Course>) => api.post<Course>('/courses/', d),
    update: (id: number, d: Partial<Course>) => api.put<Course>(`/courses/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/courses/${id}`),
  },
  assignments: {
    list: (filters?: { type?: string; status?: string; course_id?: number }) => {
      const qs = new URLSearchParams();
      if (filters?.type) qs.set('type', filters.type);
      if (filters?.status) qs.set('status', filters.status);
      if (filters?.course_id) qs.set('course_id', String(filters.course_id));
      const q = qs.toString();
      return api.get<Assignment[]>(`/assignments${q ? `?${q}` : ''}`);
    },
    byCourse: (cid: number) => api.get<Assignment[]>(`/courses/${cid}/assignments`),
    create: (d: Partial<Assignment>) => api.post<Assignment>('/assignments', d),
    update: (id: number, d: Partial<Assignment>) => api.put<Assignment>(`/assignments/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/assignments/${id}`),
    setStatus: (id: number, status: string) => api.post<Assignment>(`/assignments/${id}/status`, { status }),
    complete: (id: number) => api.post<Assignment>(`/assignments/${id}/complete`),
    attach: (id: number, file: File) => {
      const form = new FormData();
      form.append('file', file);
      return fetch(`${BASE}/assignments/${id}/attachment`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      }).then((r) => {
        if (!r.ok) throw new Error(`Attach ${r.status}: ${r.statusText}`);
        return r.json();
      }) as Promise<Assignment>;
    },
  },
  exams: {
    list: () => api.get<Exam[]>('/exams'),
    byCourse: (cid: number) => api.get<Exam[]>(`/courses/${cid}/exams`),
  },
  notes: {
    list: () => api.get<Note[]>('/notes'),
    byCourse: (cid: number) => api.get<Note[]>(`/courses/${cid}/notes`),
    create: (d: Partial<Note>) => api.post<Note>('/notes', d),
    update: (id: number, d: Partial<Note>) => api.put<Note>(`/notes/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/notes/${id}`),
    pin: (id: number) => api.put<{ id: number; pinned: boolean }>(`/notes/${id}/pin`, {}),
  },
  goals: {
    list: (habitId?: number) => api.get<Goal[]>(`/goals${habitId !== undefined ? `?habit_id=${habitId}` : ''}`),
    create: (d: Partial<Goal>) => api.post<Goal>('/goals', d),
    update: (id: number, d: Partial<Goal>) => api.put<Goal>(`/goals/${id}`, d),
    complete: (id: number) => api.post<Goal>(`/goals/${id}/complete`),
    delete: (id: number) => api.del<{ ok: boolean }>(`/goals/${id}`),
    byHabit: (habitId: number) => api.get<Goal[]>(`/goals?habit_id=${habitId}`),
  },
  tasks: {
    list: () => api.get<Task[]>('/tasks'),
    create: (d: Partial<Task>) => api.post<Task>('/tasks', d),
    update: (id: number, d: Partial<Task>) => api.put<Task>(`/tasks/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/tasks/${id}`),
  },
  reminders: {
    list: () => api.get<Reminder[]>('/reminders'),
    create: (d: Partial<Reminder>) => api.post<Reminder>('/reminders', d),
    update: (id: number, d: Partial<Reminder>) => api.put<Reminder>(`/reminders/${id}`, d),
  },
  dailyLogs: {
    list: () => api.get<DailyLog[]>('/daily-logs'),
    create: (d: Partial<DailyLog>) => api.post<DailyLog>('/daily-logs', d),
    update: (id: number, d: Partial<DailyLog>) => api.put<DailyLog>(`/daily-logs/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/daily-logs/${id}`),
    stats: () => api.get<DailyLogStats>('/daily-logs/stats'),
  },
  events: {
    list: () => api.get<LifePlannerEvent[]>('/events'),
    create: (d: Partial<LifePlannerEvent>) => api.post<LifePlannerEvent>('/events', d),
    update: (id: number, d: Partial<LifePlannerEvent>) => api.put<LifePlannerEvent>(`/events/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/events/${id}`),
    today: () => api.get<LifePlannerEvent[]>('/events/today'),
  },
  lifePlanner: {
    summary: () => api.get<LifePlannerSummary>('/life-planner/summary'),
    quickTasks: () => api.get<QuickTask[]>('/quick-tasks'),
  },
  eisenhower: {
    matrix: () => api.get<EisenhowerMatrix>('/eisenhower/matrix'),
    completeTask: (id: number) => api.post<Task>(`/eisenhower/tasks/${id}/complete`),
  },
  habits: {
    list: (includeArchived = false) => api.get<Habit[]>(`/habits${includeArchived ? '?include_archived=true' : ''}`),
    byType: (type: 'good' | 'bad') => api.get<Habit[]>(`/habits?type=${type}`),
    good: () => api.get<Habit[]>('/habits/good'),
    bad: () => api.get<Habit[]>('/habits/bad'),
    today: () => api.get<HabitTodayItem[]>('/habits/today'),
    create: (d: Partial<Habit>) => api.post<Habit>('/habits', d),
    update: (id: number, d: Partial<Habit>) => api.put<Habit>(`/habits/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/habits/${id}`),
    archive: (id: number) => api.post<Habit>(`/habits/${id}/archive`),
    unarchive: (id: number) => api.post<Habit>(`/habits/${id}/unarchive`),
    setGoal: (habitId: number, goal: string) => api.put<Habit>(`/habits/${habitId}/goal`, { goal }),
    logs: (habitId: number) => api.get<HabitLog[]>(`/habits/${habitId}/logs`),
    stats: (habitId: number) => api.get<HabitStats>(`/habits/${habitId}/stats`),
    heatmap: (habitId: number) => api.get<HabitHeatmap>(`/habits/${habitId}/heatmap`),
    logToday: (habitId: number) => api.post<HabitLog>('/habit-logs', { habit_id: habitId, date: toIso(new Date()), completed: true }),
    logHabit: (habitId: number, date?: string) =>
      api.post<HabitLog>('/habit-logs', { habit_id: habitId, date: date ?? toIso(new Date()), completed: true }),
    updateLog: (logId: number, d: Partial<HabitLog>) => api.put<HabitLog>(`/habit-logs/${logId}`, d),
    deleteLog: (logId: number) => api.del<{ ok: boolean }>(`/habit-logs/${logId}`),
    calendar: (type: 'good' | 'bad', start?: string, end?: string) => {
      const params = new URLSearchParams();
      params.set('type', type);
      if (start) params.set('start', start);
      if (end) params.set('end', end);
      return api.get<HabitCalendarDay[]>(`/habit-logs/calendar?${params.toString()}`);
    },
    reorder: (logIds: number[]) => api.post<{ ok: boolean; reordered: number }>('/habit-logs/reorder', { log_ids: logIds }),
  },
  pomodoro: {
    list: () => api.get<PomodoroSession[]>('/pomodoro-sessions'),
    create: (d: Partial<PomodoroSession>) => api.post<PomodoroSession>('/pomodoro-sessions', d),
  },
  fitness: {
    workouts: () => api.get<Workout[]>('/workouts'),
    createWorkout: (d: Partial<Workout>) => api.post<Workout>('/workouts', { ...d, user_id: 1 }),
    goals: () => api.get<FitnessGoal[]>('/fitness-goals'),
    createGoal: (d: Partial<FitnessGoal>) => api.post<FitnessGoal>('/fitness-goals', { ...d, user_id: 1 }),
    updateGoal: (id: number, d: Partial<FitnessGoal>) => api.put<FitnessGoal>(`/fitness-goals/${id}`, { ...d, user_id: 1 }),
  },
  // ----- Fitness Hub endpoints (99-phase plan, Phases 46-48) -----
  fitnessHub: {
    summary: () => api.get<FitnessHubSummary>('/fitness-hub/summary'),
    exercises: (muscleGroupId?: number) =>
      api.get<Exercise[]>(`/exercises${muscleGroupId !== undefined ? `?muscle_group_id=${muscleGroupId}` : ''}`),
    createExercise: (d: Partial<Exercise>) => api.post<Exercise>('/exercises', { ...d, user_id: 1 }),
    updateExercise: (id: number, d: Partial<Exercise>) => api.put<Exercise>(`/exercises/${id}`, { ...d, user_id: 1 }),
    deleteExercise: (id: number) => api.del<{ ok: boolean }>(`/exercises/${id}`),
    muscleGroups: () => api.get<MuscleGroup[]>('/muscle-groups'),
    createMuscleGroup: (d: Partial<MuscleGroup>) => api.post<MuscleGroup>('/muscle-groups', { ...d, user_id: 1 }),
    muscleGroupExercises: (groupId: number) => api.get<Exercise[]>(`/muscle-groups/${groupId}/exercises`),
    workoutSplits: (weekNumber?: number) =>
      api.get<WorkoutSplit[]>(`/workout-splits${weekNumber !== undefined ? `?week_number=${weekNumber}` : ''}`),
    createWorkoutSplit: (d: Partial<WorkoutSplit>) => api.post<WorkoutSplit>('/workout-splits', { ...d, user_id: 1 }),
    updateWorkoutSplit: (id: number, d: Partial<WorkoutSplit>) => api.put<WorkoutSplit>(`/workout-splits/${id}`, { ...d, user_id: 1 }),
    expenses: () => api.get<Expense[]>('/expenses'),
    createExpense: (d: Partial<Expense>) => api.post<Expense>('/expenses', { ...d, user_id: 1 }),
    deleteExpense: (id: number) => api.del<{ ok: boolean }>(`/expenses/${id}`),
    expensesSummary: () => api.get<ExpenseSummary>('/expenses/summary'),
    personalRecords: () => api.get<PersonalRecord[]>('/personal-records'),
    createPersonalRecord: (d: Partial<PersonalRecord>) => api.post<PersonalRecord>('/personal-records', { ...d, user_id: 1 }),
    dietPlans: () => api.get<DietPlan[]>('/diet-plans'),
    activeDietPlan: () => api.get<DietPlan | null>('/diet-plans/active'),
    createDietPlan: (d: Partial<DietPlan>) => api.post<DietPlan>('/diet-plans', { ...d, user_id: 1 }),
    updateDietPlan: (id: number, d: Partial<DietPlan>) => api.put<DietPlan>(`/diet-plans/${id}`, { ...d, user_id: 1 }),
    weightGoal: (userId: number) => api.get<WeightGoal>(`/users/${userId}/weight-goal`),
    updateWeightGoal: (userId: number, d: Partial<WeightGoal>) =>
      api.put<WeightGoal>(`/users/${userId}/weight-goal`, {
        initial_weight: d.initial,
        current_weight: d.current,
        target_weight: d.target,
      }),
    membership: (userId: number) => api.get<Membership>(`/users/${userId}/membership`),
  },
  journal: {
    list: () => api.get<JournalEntry[]>('/journal-entries'),
    create: (d: Partial<JournalEntry>) => api.post<JournalEntry>('/journal-entries', { ...d, user_id: 1 }),
  },
  quests: {
    list: (status?: string, priority?: string, category?: string) => {
      const params = new URLSearchParams();
      if (status) params.set('status', status);
      if (priority) params.set('priority', priority);
      if (category) params.set('category', category);
      const qs = params.toString();
      return api.get<Quest[]>(`/quests${qs ? '?' + qs : ''}`);
    },
    create: (d: Partial<Quest>) => api.post<Quest>('/quests', { ...d, user_id: 1 }),
    update: (id: number, d: Partial<Quest>) => api.put<Quest>(`/quests/${id}`, { ...d, user_id: 1 }),
    delete: (id: number) => api.del<{ ok: boolean }>(`/quests/${id}`),
    complete: (id: number) => api.post<Quest>(`/quests/${id}/complete`),
  },
  projects: {
    list: () => api.get<Project[]>('/projects'),
    create: (d: Partial<Project>) => api.post<Project>('/projects', d),
    update: (id: number, d: Partial<Project>) => api.put<Project>(`/projects/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/projects/${id}`),
    summary: (id: number) => api.get<ProjectSummary>(`/projects/${id}/summary`),
    tasks: (id: number) => api.get<ProjectTask[]>(`/projects/${id}/tasks`),
    createTask: (d: Partial<ProjectTask>) => api.post<ProjectTask>('/project-tasks', d),
    updateTask: (id: number, d: Partial<ProjectTask>) => api.put<ProjectTask>(`/project-tasks/${id}`, d),
    deleteTask: (id: number) => api.del<{ ok: boolean }>(`/project-tasks/${id}`),
  },
  lifeAreas: {
    list: () => api.get<LifeArea[]>('/life-areas'),
    update: (id: number, d: Partial<LifeArea>) => api.put<LifeArea>(`/life-areas/${id}`, d),
    goals: (areaId: number) => api.get<Goal[]>(`/life-areas/${areaId}/goals`),
    complete: (id: number) => api.post<LifeArea>(`/life-areas/${id}/complete`),
  },
  users: {
    gamification: (userId?: number) =>
      api.get<GamificationProfile>(`/quest-centre/gamification${userId ? `?user_id=${userId}` : ''}`),
  },
  questCentre: {
    statusWindow: () => api.get<StatusWindow>('/quest-centre/status-window'),
    progress: () => api.get<ProgressReport>('/quest-centre/progress'),
    priorityWindow: () => api.get<PriorityWindow>('/quest-centre/priority-window'),
    quickActions: () => api.get<QuickActionsResponse>('/quest-centre/quick-actions'),
    lifeAreas: () => api.get<QuestCentreLifeArea[]>('/quest-centre/life-areas'),
    calendar: () => api.get<QuestCentreCalendar>('/quest-centre/calendar'),
    gamification: (userId?: number) =>
      api.get<GamificationProfile>(`/quest-centre/gamification${userId ? `?user_id=${userId}` : ''}`),
  },
  characters: {
    get: (userId: number) => api.get<Character>(`/characters/${userId}`),
    addXp: (userId: number, amount: number) => api.post<Character>(`/characters/${userId}/xp`, { amount }),
  },
  habitTracker: {
    statusWindow: () => api.get<HabitTrackerStatusWindow>('/habit-tracker/status-window'),
    summary: () => api.get<HabitTrackerSummary>('/habit-tracker/summary'),
  },
  rewards: {
    list: (available?: boolean) => api.get<Reward[]>(`/rewards${available !== undefined ? `?available=${available}` : ''}`),
    create: (d: Partial<Reward>) => api.post<Reward>('/rewards', { ...d, user_id: 1 }),
    update: (id: number, d: Partial<Reward>) => api.put<Reward>(`/rewards/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/rewards/${id}`),
    claim: (rewardId: number, userId: number) => api.post<Reward>(`/rewards/${rewardId}/claim?user_id=${userId}`),
    claimed: () => api.get<Reward[]>('/rewards/claimed'),
  },
  missions: {
    list: (status?: string) => api.get<Mission[]>(`/missions${status ? `?status=${status}` : ''}`),
    create: (d: Partial<Mission>) => api.post<Mission>('/missions', { ...d, user_id: 1 }),
    update: (id: number, d: Partial<Mission>) => api.put<Mission>(`/missions/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/missions/${id}`),
    listTasks: (missionId: number) => api.get<MissionTask[]>(`/missions/${missionId}/tasks`),
    createTask: (missionId: number, d: Partial<MissionTask>) => api.post<MissionTask>(`/missions/${missionId}/tasks`, d),
    updateTask: (taskId: number, d: Partial<MissionTask>) => api.put<MissionTask>(`/mission-tasks/${taskId}`, d),
    deleteTask: (taskId: number) => api.del<{ ok: boolean }>(`/mission-tasks/${taskId}`),
    complete: (id: number) => api.post<Mission>(`/missions/${id}/complete`),
    linked: (id: number) => api.get<Quest[]>(`/missions/${id}/linked`),
  },
  schedule: {
    list: (dayOfWeek?: number) => api.get<ScheduleEvent[]>(`/schedule${dayOfWeek !== undefined ? `?day_of_week=${dayOfWeek}` : ''}`),
    create: (d: Partial<ScheduleEvent>) => api.post<ScheduleEvent>('/schedule', { ...d, user_id: 1 }),
    update: (id: number, d: Partial<ScheduleEvent>) => api.put<ScheduleEvent>(`/schedule/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/schedule/${id}`),
  },
  vault: {
    summary: () => api.get<VaultSummary>('/vault/summary'),
    tasks: (tab: string) => api.get<Task[]>(`/vault/tasks?tab=${tab}`),
    calendar: () => api.get<VaultCalendar>('/vault/calendar'),
    database: () => api.get<DatabaseCounts>('/vault/database'),
  },
  // ----- Global unified search (Phase 3, Idea 30) -----
  search: {
    global: (q: string, domains?: string[]) =>
      api.post<GlobalSearchResponse>('/search', { query: q, domains }),
  },
  // ----- Second Brain / Knowledge Base (Phase 1) -----
  kb: {
    sources: {
      list: () => api.get<{ items: KbSource[]; total: number }>('/kb/sources'),
      get: (id: number) => api.get<KbSource>(`/kb/sources/${id}`),
      create: (d: { name: string; source_type?: string; root_path: string; enabled?: boolean; sync_type?: string }) =>
        api.post<KbSource>('/kb/sources', d),
      update: (id: number, d: { name?: string; source_type?: string; root_path?: string; enabled?: boolean; sync_type?: string }) =>
        api.put<KbSource>(`/kb/sources/${id}`, d),
      remove: (id: number) => api.del<{ ok: boolean; deleted_documents: number }>(`/kb/sources/${id}`),
      scan: (id: number) => api.post<KbScanResult>(`/kb/sources/${id}/scan`),
      // Phase 9 (Idea 89): external repo sync.
      sync: (id: number) => api.post<KbSourceSyncResult>(`/kb/sources/${id}/sync`),
      syncStatus: (id: number) => api.get<KbSourceSyncStatus>(`/kb/sources/${id}/sync-status`),
    },
    documents: {
      list: (params?: { source_id?: number; status?: string; q?: string; page?: number; page_size?: number }) => {
        const qs = new URLSearchParams();
        if (params?.source_id) qs.set('source_id', String(params.source_id));
        if (params?.status) qs.set('status', params.status);
        if (params?.q) qs.set('q', params.q);
        if (params?.page) qs.set('page', String(params.page));
        if (params?.page_size) qs.set('page_size', String(params.page_size));
        const q = qs.toString();
        return api.get<KbDocumentListResponse>(`/kb/documents${q ? `?${q}` : ''}`);
      },
      get: (id: number) => api.get<KbDocument>(`/kb/documents/${id}`),
      remove: (id: number) => api.del<{ ok: boolean }>(`/kb/documents/${id}`),
      upload: (file: File, sourceId?: number) => {
        const form = new FormData();
        form.append('file', file);
        return fetch(`${BASE}/kb/documents/upload${sourceId ? `?source_id=${sourceId}` : ''}`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: form,
        }).then((r) => {
          if (!r.ok) throw new Error(`Upload ${r.status}: ${r.statusText}`);
          return r.json();
        }) as Promise<KbUploadResult>;
      },
      chunks: (id: number) => api.get<KbChunk[]>(`/kb/documents/${id}/chunks`),
      versions: (id: number) => api.get<KbVersion[]>(`/kb/documents/${id}/versions`),
      restore: (id: number, versionId: number) =>
        api.post<{ document: KbDocument; new_version_seq: number }>(`/kb/documents/${id}/restore?version_id=${versionId}`),
      diff: (id: number, fromVersion: number, toVersion: number) =>
        api.get<KbDiffResponse>(`/kb/documents/${id}/diff?from_version=${fromVersion}&to_version=${toVersion}`),
      reindex: (id: number) => api.post<KbJob>(`/kb/documents/${id}/reindex`),
      // Phase 4 (Idea 40): file a braindump draft (title/source/tags → new).
      file: (id: number, d: { title?: string; source_id?: number | null; tags?: string[] }) =>
        api.post<KbDocument>(`/kb/documents/${id}/file`, d),
      // Phase 4 (Idea 40): AI-assisted section splitting of a draft.
      split: (id: number) =>
        api.post<{ document_id: number; sections_applied: number; fallback: boolean; sections: { title: string; char_start: number }[] }>(
          `/kb/documents/${id}/split`,
        ),
      // Phase 4 (Idea 37): aggregated concepts + related notes for the reader sidebar.
      links: (id: number) => api.get<KbLinksResponse>(`/kb/documents/${id}/links`),
    },
    papers: {
      import: (arxivId: string, sourceId?: number) =>
        api.post<{ document: KbDocument; metadata_fetched: boolean }>('/kb/papers/import', {
          arxiv_id: arxivId,
          source_id: sourceId ?? null,
        }),
    },
    jobs: {
      list: () => api.get<{ items: KbJob[]; total: number }>('/kb/jobs'),
      get: (id: number) => api.get<KbJob>(`/kb/jobs/${id}`),
    },
    graph: {
      list: (params?: { source?: string; tag?: string; concept?: string; relation?: string; limit?: number }) => {
        const qs = new URLSearchParams();
        if (params?.source) qs.set('source', params.source);
        if (params?.tag) qs.set('tag', params.tag);
        if (params?.concept) qs.set('concept', params.concept);
        if (params?.relation) qs.set('relation', params.relation);
        if (params?.limit !== undefined) qs.set('limit', String(params.limit));
        const q = qs.toString();
        return api.get<KbGraphResponse>(`/kb/graph${q ? `?${q}` : ''}`);
      },
    },
    stats: () => api.get<KbStats>('/kb/stats'),
    related: {
      list: (documentId: number, relation?: string, infer = true) => {
        const qs = new URLSearchParams();
        if (relation) qs.set('relation', relation);
        qs.set('infer', String(infer));
        return api.get<KbRelatedResponse>(`/kb/documents/${documentId}/related?${qs.toString()}`);
      },
    },
    tags: {
      forDocument: (documentId: number) => api.get<KbDocumentTagsResponse>(`/kb/documents/${documentId}/tags`),
      apply: (documentId: number, tagIds: number[]) =>
        api.post<KbDocumentTagsResponse>(`/kb/documents/${documentId}/tags`, {
          document_id: documentId,
          tag_ids: tagIds,
        }),
      reject: (documentId: number, tagId: number) =>
        api.del<{ ok: boolean; removed: number }>(`/kb/documents/${documentId}/tags/${tagId}`),
    },
    concepts: {
      list: (q = '', page = 1, pageSize = 50) =>
        api.get<{ items: KbConcept[]; total: number; page: number; page_size: number }>(
          `/kb/concepts?q=${encodeURIComponent(q)}&page=${page}&page_size=${pageSize}`,
        ),
    },
    metadata: {
      update: (documentId: number, d: KbMetadataUpdate) =>
        api.put<Record<string, unknown>>(`/kb/documents/${documentId}/metadata`, d),
    },
    duplicates: {
      list: () => api.get<KbDuplicatesResponse>('/kb/duplicates'),
      scan: () => api.post<KbDuplicatesResponse>('/kb/duplicates/scan'),
      merge: (keepId: number, mergeIds: number[]) =>
        api.post<{ ok: boolean; merged: number }>('/kb/duplicates/merge', {
          keep_id: keepId,
          merge_ids: mergeIds,
        }),
      archive: (documentId: number) => api.post<{ ok: boolean }>(`/kb/duplicates/${documentId}/archive`),
    },
    reindex: {
      source: (sourceId: number) => api.post<KbJob>(`/kb/admin/reindex?source_id=${sourceId}`),
      documents: (documentIds: number[]) =>
        api.post<KbJob>(`/kb/admin/reindex?document_ids=${documentIds.join(',')}`),
      backfill: (sourceId?: number) =>
        api.post<KbJob>(`/kb/admin/backfill${sourceId ? `?source_id=${sourceId}` : ''}`),
    },
    // ----- Phase 3: search & retrieval (Ideas 21-25, 29) -----
    search: {
      run: (q: string, opts?: { mode?: KbSearchMode; page?: number; page_size?: number }) =>
        api.post<KbSearchResponse>('/kb/search', {
          query: q,
          mode: opts?.mode ?? 'hybrid',
          page: opts?.page ?? 1,
          page_size: opts?.page_size ?? 20,
        }),
      feedback: (d: { query: string; mode?: string; chunk_id?: number; clicked?: boolean; rating?: number }) =>
        api.post<{ ok: boolean; event_id: number }>('/kb/search/feedback', d),
      events: () => api.get<{ items: KbSearchEventItem[]; total: number }>('/kb/search/events'),
      purge: () => api.del<{ ok: boolean; deleted: number }>('/kb/search/events'),
    },
    // ----- Phase 3: knowledge health & gaps (Ideas 27-28) -----
    health: () => api.get<KbHealth>('/kb/health'),
    gaps: {
      all: () => api.get<KbGapsResponse>('/kb/gaps'),
      concepts: (limit = 20) => api.get<{ items: KbConceptGap[] }>(`/kb/gaps/concepts?limit=${limit}`),
    },
    // ----- Phase 4: note intelligence & content generation (Ideas 31-40) -----
    summaries: {
      get: (documentId: number) => api.get<KbSummaryResponse>(`/kb/documents/${documentId}/summary`),
      regenerate: (documentId: number) => api.post<KbSummaryResponse>(`/kb/documents/${documentId}/summary`),
    },
    explain: {
      run: (d: { concept: string; depth?: string; document_ids?: number[] }) =>
        api.post<KbExplainResponse>('/kb/explain', d),
      personalized: (d: { concept: string; depth?: string; document_ids?: number[] }) =>
        api.post<KbPersonalizedExplainResponse>('/kb/explain/personalized', d),
    },
    quizzes: {
      generate: (documentId: number, numQuestions = 10, difficulty = 'medium') =>
        api.post<Quiz & { document_id: number }>('/kb/quizzes', {
          document_id: documentId,
          num_questions: numQuestions,
          difficulty,
        }),
      sourceDocument: (quizId: number) => api.get<KbDocument>(`/kb/quizzes/${quizId}/document`),
    },
    flashcards: {
      generate: (documentId: number) =>
        api.post<KbFlashcardGenerateResult>(`/kb/documents/${documentId}/flashcards`),
      candidates: (status = 'pending') =>
        api.get<{ items: KbFlashcardCandidate[] }>(`/kb/flashcards/candidates?status=${status}`),
      review: (d: { approve?: number[]; reject?: number[]; deck_id?: number }) =>
        api.post<{ approved: number; rejected: number; deck_id: number | null }>('/kb/flashcards/review', d),
    },
    dailyNotes: {
      get: (date: string) => api.get<KbDailyNotes>(`/kb/daily-notes?date=${encodeURIComponent(date)}`),
      today: () => api.get<KbDailyNotes>('/kb/daily-notes/today'),
    },
    citations: {
      list: (params?: { year?: number; venue?: string }) => {
        const qs = new URLSearchParams();
        if (params?.year) qs.set('year', String(params.year));
        if (params?.venue) qs.set('venue', params.venue);
        const q = qs.toString();
        return api.get<{ items: KbCitation[]; total: number }>(`/kb/citations${q ? `?${q}` : ''}`);
      },
      forDocument: (documentId: number) =>
        api.get<{ items: KbCitation[]; total: number }>(`/kb/documents/${documentId}/citations`),
      exportUrl: () => `${BASE}/kb/citations/export?format=bibtex`,
    },
    edges: {
      create: (d: { source_document_id: number; target_id: number; relation?: string; target_type?: string }) =>
        api.post<{ id: number; ok: boolean }>('/kb/edges', d),
      remove: (edgeId: number) => api.del<{ ok: boolean }>(`/kb/edges/${edgeId}`),
    },
    mindmap: {
      get: (documentId: number) => api.get<KbMindMapNode>(`/kb/documents/${documentId}/mindmap`),
      exportUrl: (documentId: number, format: 'markdown' | 'opml') =>
        `${BASE}/kb/documents/${documentId}/mindmap?format=${format}`,
    },
    quality: {
      document: (documentId: number) => api.get<KbQualityResult>(`/kb/documents/${documentId}/quality`),
      list: () => api.get<{ items: KbQualityItem[]; total: number }>('/kb/quality'),
      generateSuggestions: (documentId: number) =>
        api.post<{ document_id: number; generated: number; items: KbQualitySuggestion[] }>(
          `/kb/documents/${documentId}/quality/suggestions`,
        ),
      dismissSuggestion: (suggestionId: number) =>
        api.post<{ ok: boolean }>(`/kb/quality/suggestions/${suggestionId}/dismiss`),
    },
    // ----- Phase 7: AI Tutor & Assessment (Ideas 61-70) -----
    tutor: {
      chat: (d: { message: string; session_id?: number | null }) =>
        api.post<TutorChatResponse>('/kb/tutor/chat', d),
      doubt: (d: { question: string; step_where_stuck?: string | null }) =>
        api.post<TutorDoubtResponse>('/kb/tutor/doubt', d),
      sessions: () => api.get<{ items: TutorSessionItem[] }>('/kb/tutor/sessions'),
    },
    practice: {
      generate: (d: { topic_id: number; count?: number; difficulty?: string }) =>
        api.post<PracticeGenerateResponse>('/kb/practice/generate', d),
      questions: (params?: { topic_id?: number; status?: string }) => {
        const qs = new URLSearchParams();
        if (params?.topic_id) qs.set('topic_id', String(params.topic_id));
        if (params?.status) qs.set('status', params.status);
        const q = qs.toString();
        return api.get<{ items: PracticeQuestionItem[] }>(`/kb/practice/questions${q ? `?${q}` : ''}`);
      },
      approve: (id: number) => api.post<{ ok: boolean; question: PracticeQuestionItem }>(`/kb/practice/${id}/approve`),
      reject: (id: number) => api.post<{ ok: boolean; question: PracticeQuestionItem }>(`/kb/practice/${id}/reject`),
      session: (topicId: number) =>
        api.post<PracticeSessionResponse>('/kb/practice/session', { topic_id: topicId }),
      answer: (d: { topic_id: number; tier: string; correct: boolean }) =>
        api.post<PracticeAnswerResponse>('/kb/practice/answer', d),
      mistakeAnalysis: (d: { question_id: number; student_answer: string }) =>
        api.post<MistakeAnalysisResponse>('/kb/practice/mistake-analysis', d),
    },
    mocks: {
      build: (d: { subject_id: number; title?: string; question_count?: number; duration_mins?: number }) =>
        api.post<{ mock: MockTestItem }>('/kb/mocks/build', d),
      list: () => api.get<{ items: MockTestItem[] }>('/kb/mocks'),
      start: (mockId: number) => api.post<{ attempt: MockAttemptItem }>(`/kb/mocks/${mockId}/start`),
      submit: (attemptId: number, answers: Record<number, string>) =>
        api.post<MockSubmitResponse>(`/kb/mocks/attempts/${attemptId}/submit`, { answers }),
      attempts: (mockId: number) => api.get<{ items: MockAttemptItem[] }>(`/kb/mocks/${mockId}/attempts`),
    },
    interview: {
      start: (d: { skill: string; level?: string }) =>
        api.post<{ session: InterviewSession }>('/kb/interview/start', d),
      answer: (sessionId: number, index: number, answer: string) =>
        api.post<InterviewAnswerResponse>(`/kb/interview/${sessionId}/answer`, { index, answer }),
      finish: (sessionId: number) =>
        api.post<InterviewFinishResponse>(`/kb/interview/${sessionId}/finish`),
    },
    skills: {
      map: (subjectId: number) => api.post<SkillsResponse>('/kb/skills/map', { subject_id: subjectId }),
      profile: () => api.get<SkillsResponse>('/kb/skills'),
      export: (fmt: 'markdown' | 'json' = 'markdown') =>
        api.get<SkillsExportResponse>(`/kb/skills/export?fmt=${fmt}`),
    },
    // ----- Phase 8: Personalization & Learning Memory (Ideas 71-80) -----
    preferences: {
      get: () => api.get<UserPreference>('/users/me/preferences'),
      update: (d: Partial<UserPreference>) => api.put<UserPreference>('/users/me/preferences', d),
      nudge: (feedback: string) =>
        api.post<{ provenance: string; changed: Record<string, unknown> }>('/kb/preferences/nudge', { feedback }),
    },
    memory: {
      get: (limit = 200) => api.get<{ items: KbMemoryItem[] }>(`/kb/memory?limit=${limit}`),
      bump: (d: { concept_ids: number[]; delta?: number; source?: string }) =>
        api.post<{ touched: number[] }>('/kb/memory/bump', d),
      decay: () => api.post<{ decayed: number }>('/kb/memory/decay'),
      // Phase 10 (Idea 92): episodic long-term memory (timeline + consolidation).
      timeline: (limit = 50) => api.get<KbMemoryTimeline>(`/kb/memory/timeline?limit=${limit}`),
      consolidate: () => api.post<{ appended: number; episodes: number; facts: number; folded: number }>('/kb/memory/consolidate'),
    },
    recommend: {
      next: (limit = 1) => api.get<{ items: KbRecommendItem[] }>(`/kb/recommend/next?limit=${limit}`),
    },
    connect: {
      suggestions: (documentId: number) =>
        api.get<KbConnectSuggestionsResponse>(`/kb/documents/${documentId}/connect-suggestions`),
      confirm: (documentId: number, targetDocumentId: number, relation = 'RELATED') =>
        api.post<{ edge_id: number | null; source_document_id: number; target_document_id: number; relation: string; provenance: string }>(
          `/kb/documents/${documentId}/connect`,
          { target_document_id: targetDocumentId, relation },
        ),
    },
    missingNotes: {
      list: (status = 'suggested') =>
        api.get<{ items: KbMissingNoteSuggestion[] }>(`/kb/suggestions/missing-notes?status=${status}`),
      generate: (limit = 10) =>
        api.post<{ items: KbMissingNoteSuggestion[] }>(`/kb/suggestions/missing-notes?limit=${limit}`),
      accept: (id: number) =>
        api.post<{ suggestion_id: number; document_id: number; title: string; status: string }>(
          `/kb/suggestions/${id}/accept`,
        ),
      dismiss: (id: number) => api.post<{ id: number; status: string }>(`/kb/suggestions/${id}/dismiss`),
    },
    outdated: {
      scan: () => api.post<{ scanned: boolean; created: number; items: { id: number; document_id: number; reason: string; evidence: Record<string, unknown> }[] }>(
        '/kb/outdated/scan',
      ),
      review: (status = 'open') =>
        api.get<{ items: KbOutdatedNote[] }>(`/kb/outdated/review?status=${status}`),
      resolve: (noteId: number, action: 'updated' | 'archived' | 'dismissed') =>
        api.post<{ id: number; document_id: number; status: string }>(`/kb/outdated/${noteId}/resolve`, { action }),
    },
    adapt: {
      // Backend AdaptRoadmapRequest accepts null for both fields.
      roadmap: (profileId: number, d?: { weekly_budget?: number | null; deadline?: string | null }) =>
        api.post<{ adaptation: KbAdaptation }>(`/subjects-ai/${profileId}/roadmap/adapt`, d ?? {}),
    },
    // ----- Phase 9: Automation (Ideas 81-90) -----
    automation: {
      jobs: () => api.get<{ jobs: KbAutomationJob[] }>('/kb/automation/jobs'),
      run: (d: { mode: 'one' | 'all'; name?: string | null; force?: boolean }) =>
        api.post<KbAutomationRunResult>('/kb/automation/run', d),
    },
    // ----- Phase 10: Advanced AI, Analytics & Platform (Ideas 91-100) -----
    agents: {
      run: (request: string) => api.post<KbAgentRun>('/kb/agents/run', { request }),
      runs: () => api.get<{ items: KbAgentRun[] }>('/kb/agents/runs'),
    },
    context: {
      get: () => api.get<KbContextBundle>('/kb/context'),
      put: (d: { active_subject_id?: number | null; active_subject_name?: string | null }) =>
        api.put<{ saved: Record<string, unknown>; bundle: KbContextBundle }>('/kb/context', d),
    },
    research: {
      explain: (d: { document_id?: number; arxiv_id?: string; question?: string }) =>
        api.post<KbResearchExplainResult>('/kb/research/explain', d),
      related: (documentId: number, limit = 5) =>
        api.get<{ document_id: number; items: KbRelatedPaper[] }>(`/kb/research/related?document_id=${documentId}&limit=${limit}`),
    },
    recommendations: {
      list: (limit = 8) => api.get<{ items: KbRecommendationItem[]; total: number; weights: Record<string, number> }>(`/kb/recommendations?limit=${limit}`),
      feedback: (itemId: string, action: 'accept' | 'skip') =>
        api.post<{ ok: boolean; item_id: string; action: string }>(`/kb/recommendations/${itemId}/feedback`, { action }),
    },
    reflections: {
      list: () => api.get<{ items: KbReflection[] }>('/kb/reflections'),
      generate: () => api.post<KbReflection>('/kb/reflections/generate', {}),
      adjust: () => api.post<{ applied: unknown[]; count: number }>('/kb/reflections/adjust'),
      derivedGoals: () => api.get<{ items: KbDerivedGoal[] }>('/kb/goals/derived'),
      confirmGoal: (d: KbDerivedGoal) => api.post<{ ok: boolean; goal_id: number }>('/kb/goals/derived/confirm', d),
      goals: () => api.get<{ items: KbGoalItem[] }>('/kb/goals'),
      goalProgress: (goalId: number) => api.get<{ goal_id: number; title: string; progress_percentage: number; topics_mastered: number; topics_total: number }>(`/kb/goals/${goalId}/progress`),
    },
    forecast: {
      get: (subjectId: number) => api.get<KbForecast>(`/kb/forecast/${subjectId}`),
      scan: () => api.post<{ processed: number; at_risk: number; alerted: number }>('/kb/forecast/scan'),
    },
    observability: {
      dashboard: () => api.get<KbObservabilityPayload>('/kb/observability'),
      report: () => api.get<{ week_start: string; aggregate: KbObservabilityPayload; top_failures: number; generated_at: string }>('/kb/observability/report'),
      feedback: (logId: number, feedback: -1 | 0 | 1) =>
        api.post<{ ok: boolean; log_id: number; feedback: number }>(`/kb/observability/${logId}/feedback`, { feedback }),
      prompts: () => api.get<{ items: KbPromptVersion[] }>('/kb/prompts'),
      pinPrompt: (d: { feature: string; template: string; version?: number | null }) =>
        api.post<{ ok: boolean; feature: string; version: number; is_active: boolean }>('/kb/prompts', d),
    },
  },
  // ----- Phase 5: Subject Management Core (Ideas 41-50) -----
  subjects: {
    import: (d: { text?: string; filename?: string }) =>
      api.post<{ profile: SubjectProfile; fallback: boolean }>('/subjects/import', d),
    importFile: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return fetch(`${BASE}/subjects/import-file`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      }).then((r) => {
        if (!r.ok) throw new Error(`Import ${r.status}: ${r.statusText}`);
        return r.json();
      }) as Promise<{ profile: SubjectProfile; fallback: boolean }>;
    },
    proposals: (status?: SubjectProfileStatus) =>
      api.get<{ items: SubjectProfile[]; total: number }>(
        `/subjects/proposals${status ? `?status=${status}` : ''}`,
      ),
    list: (params?: { semester?: string; status?: SubjectProfileStatus }) => {
      const qs = new URLSearchParams();
      if (params?.semester) qs.set('semester', params.semester);
      if (params?.status) qs.set('status', params.status);
      const q = qs.toString();
      return api.get<{ items: SubjectProfile[]; total: number }>(`/subjects${q ? `?${q}` : ''}`);
    },
    get: (profileId: number) => api.get<SubjectProfile>(`/subjects/${profileId}`),
    confirm: (profileId: number, d: { program_id?: number | null; name?: string; code?: string; credits?: number | null }) =>
      api.post<{ profile: SubjectProfile }>(`/subjects/${profileId}/confirm`, d),
    reject: (profileId: number) => api.post<{ ok: boolean; profile: SubjectProfile }>(`/subjects/${profileId}/reject`),
    topics: {
      generate: (profileId: number) =>
        api.post<{ generated: number; fallback: boolean }>(`/subjects/${profileId}/topics/generate`),
      list: (profileId: number, status?: TopicStatus) =>
        api.get<{ items: TopicItem[] }>(`/subjects/${profileId}/topics${status ? `?status=${status}` : ''}`),
      confirm: (profileId: number, topicId: number) =>
        api.post<{ ok: boolean; topic: TopicItem }>(`/subjects/${profileId}/topics/${topicId}/confirm`),
      reject: (profileId: number, topicId: number) =>
        api.post<{ ok: boolean; topic: TopicItem }>(`/subjects/${profileId}/topics/${topicId}/reject`),
      merge: (profileId: number, topicId: number, intoTopicId: number) =>
        api.post<{ ok: boolean }>(`/subjects/${profileId}/topics/${topicId}/merge`, {
          into_topic_id: intoTopicId,
        }),
      patch: (topicId: number, d: { difficulty?: string; first_pass_mins?: number; review_mins?: number; mastery_mins?: number }) =>
        api.patch<{ ok: boolean; topic: TopicItem }>(`/subjects/topics/${topicId}`, d),
      recompute: (topicId: number) =>
        api.post<{ ok: boolean; topic: TopicItem }>(`/subjects/topics/${topicId}/recompute`),
    },
    matchUnits: {
      list: (profileId: number, useEmbeddings = false) =>
        api.get<{ items: UnitMatchCandidate[] }>(
          `/subjects/${profileId}/match-units?use_embeddings=${useEmbeddings}`,
        ),
      confirm: (profileId: number, mapping: Record<string, number | null>) =>
        api.post<{ ok: boolean; topics_assigned: number }>(`/subjects/${profileId}/match-units/confirm`, {
          mapping,
        }),
    },
    dependencies: {
      get: (profileId: number) => api.get<DependencyGraph>(`/subjects/${profileId}/dependencies`),
      generate: (profileId: number) =>
        api.post<{ created: number }>(`/subjects/${profileId}/dependencies/generate`),
      add: (profileId: number, prereqTopicId: number, postreqTopicId: number) =>
        api.post<{ ok: boolean }>(`/subjects/${profileId}/dependencies`, {
          prereq_topic_id: prereqTopicId,
          postreq_topic_id: postreqTopicId,
        }),
      remove: (depId: number) => api.del<{ ok: boolean }>(`/subjects/dependencies/${depId}`),
    },
    roadmap: {
      generate: (profileId: number, d: { weekly_budget?: number | null; deadline?: string | null }) =>
        api.post<{ roadmap: RoadmapItem }>(`/subjects/${profileId}/roadmap/generate`, d),
      get: (profileId: number) =>
        api.get<{ roadmap: RoadmapItem | null }>(`/subjects/${profileId}/roadmap`),
    },
    timeBudget: (profileId: number) => api.get<TimeBudgetResponse>(`/subjects/${profileId}/time-budget`),
    pacing: (multiplier: number) => api.put<{ ok: boolean; pacing_multiplier: number }>('/subjects/me/pacing', { multiplier }),
    outcomes: {
      get: (topicId: number) => api.get<{ topic_id: number; outcomes: TopicOutcome[] }>(`/subjects/topics/${topicId}/outcomes`),
      add: (topicId: number, text: string) =>
        api.post<{ ok: boolean; outcomes: TopicOutcome[] }>(`/subjects/topics/${topicId}/outcomes`, { text }),
      expand: (topicId: number) =>
        api.post<{ ok: boolean; outcomes: TopicOutcome[] }>(`/subjects/topics/${topicId}/outcomes/expand`),
      complete: (topicId: number, index: number) =>
        api.post<{ ok: boolean; outcomes: TopicOutcome[] }>(`/subjects/topics/${topicId}/outcomes/${index}/complete`),
    },
  },
};

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

// ===== STUDENT-PLANAR domains: reading tracker, brain dump, daily schedule, notifications =====

export type BookCategory = 'reading' | 'finished' | 'want';

export interface Book {
  id: number;
  title: string;
  author: string | null;
  category: BookCategory;
  cover_url: string | null;
  file_url: string | null;
  created_at: string;
}

export interface BookInsights {
  total: number;
  finished: number;
  reading: number;
  want: number;
  completion_pct: number;
  per_author: Record<string, number>;
}

export interface BookListResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
}

export interface BrainDump {
  id: number;
  user_id: number;
  content: string | null;
  updated_at: string | null;
  // Phase 4 (Idea 40): the draft KbDocument this dump upserts, if any.
  linked_document_id?: number | null;
}

export type DailyCategory = 'School' | 'Study Time' | 'Break';
export type EnergyLevel = 'High' | 'Medium' | 'Low';

export interface DailyScheduleItem {
  id: number;
  date: string;
  time_range: string;
  activity: string;
  category: DailyCategory;
  cat_class: string | null;
  location: string | null;
  energy: EnergyLevel;
  e_class: string | null;
  notes: string | null;
  done: boolean;
  created_at: string;
}

export interface DailyScheduleStats {
  date: string;
  total: number;
  done: number;
  ratio: number;
}

export interface AppNotification {
  id: number;
  user_id: number;
  kind: string;
  title: string;
  body: string | null;
  ref_type: string | null;
  ref_id: number | null;
  read: boolean;
  created_at: string;
}

export const bookApi = {
  list: (params?: { category?: BookCategory; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set('category', params.category);
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    const q = qs.toString();
    return api.get<BookListResponse>(`/books${q ? `?${q}` : ''}`);
  },
  create: (d: { title: string; author?: string | null; category?: BookCategory }) => api.post<Book>('/books', d),
  update: (id: number, d: Partial<Omit<Book, 'id' | 'created_at'>>) => api.put<Book>(`/books/${id}`, d),
  remove: (id: number) => api.del<{ ok: boolean }>(`/books/${id}`),
  insights: () => api.get<BookInsights>('/books/insights'),
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE}/books/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    }).then((r) => {
      if (!r.ok) throw new Error(`Upload ${r.status}: ${r.statusText}`);
      return r.json();
    }) as Promise<{ url: string; filename: string }>;
  },
};

export const brainDumpApi = {
  get: () => api.get<{ content: string | null; linked_document_id?: number | null }>('/braindumps'),
  save: (content: string) => api.put<BrainDump>('/braindumps', { content }),
};

export const dailyScheduleApi = {
  list: (date: string) => api.get<DailyScheduleItem[]>(`/dailyschedule?date=${date}`),
  create: (d: {
    date: string;
    time_range: string;
    activity: string;
    category?: DailyCategory;
    location?: string | null;
    energy?: EnergyLevel;
    notes?: string | null;
  }) => api.post<DailyScheduleItem>('/dailyschedule', d),
  update: (id: number, d: Partial<Omit<DailyScheduleItem, 'id' | 'created_at'>>) =>
    api.put<DailyScheduleItem>(`/dailyschedule/${id}`, d),
  remove: (id: number) => api.del<{ ok: boolean }>(`/dailyschedule/${id}`),
  toggle: (id: number) => api.post<DailyScheduleItem>(`/dailyschedule/${id}/toggle`),
  stats: (date: string) => api.get<DailyScheduleStats>(`/dailyschedule/stats?date=${date}`),
};

export const notificationApi = {
  list: () => api.get<AppNotification[]>('/notifications'),
  unreadCount: () => api.get<{ unread: number }>('/notifications/unread-count'),
  markRead: (id: number) => api.post<AppNotification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<{ ok: boolean }>('/notifications/mark-all-read'),
  remove: (id: number) => api.del<{ ok: boolean }>(`/notifications/${id}`),
  clearAll: () => api.del<{ ok: boolean; deleted: number }>('/notifications'),
};

export interface TeacherStudentStats {
  courses: number;
  assignments: number;
  todos: number;
  books: number;
  braindump: boolean;
}

export interface TeacherStudent {
  id: number;
  name: string;
  stats: TeacherStudentStats;
}

export interface TeacherStudentDetail {
  id: number;
  name: string;
  assignments: Assignment[];
  todos: Task[];
  braindump: { content: string | null } | null;
  books: Book[];
}

export interface TeacherBroadcastResult {
  created: number;
}

function broadcastForm(payload: Record<string, unknown>, file?: File | null): FormData {
  const form = new FormData();
  Object.entries(payload).forEach(([k, v]) => {
    if (v !== undefined && v !== null) form.append(k, JSON.stringify(v));
  });
  if (file) form.append('file', file);
  return form;
}

function multipartPost(path: string, form: FormData): Promise<TeacherBroadcastResult> {
  return fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${getToken()}` },
    body: form,
  }).then((r) => {
    if (!r.ok) throw new Error(`Broadcast ${r.status}: ${r.statusText}`);
    return r.json();
  }) as Promise<TeacherBroadcastResult>;
}

export const teacherApi = {
  students: () => api.get<TeacherStudent[]>('/teacher/students'),
  studentDetail: (studentId: number) => api.get<TeacherStudentDetail>(`/teacher/students/${studentId}/detail`),
  broadcastCourses: (course: Partial<Course>, studentIds?: number[]) =>
    api.post<TeacherBroadcastResult>('/teacher/broadcast/courses', { course, student_ids: studentIds ?? null }),
  broadcastTodos: (todo: { title: string; due_date?: string | null; priority_tag?: string; subject_tag?: string }, studentIds?: number[]) =>
    api.post<TeacherBroadcastResult>('/teacher/broadcast/todos', { todo, student_ids: studentIds ?? null }),
  broadcastSchedule: (item: { date: string; time_range: string; activity: string; category?: string; energy?: string; location?: string | null; notes?: string | null }, studentIds?: number[]) =>
    api.post<TeacherBroadcastResult>('/teacher/broadcast/schedule', { item, student_ids: studentIds ?? null }),
  broadcastAssignments: (assignment: { title: string; description?: string; due_date?: string; status?: string; type?: string }, studentIds?: number[], file?: File | null) =>
    multipartPost('/teacher/broadcast/assignments', broadcastForm({ assignment, student_ids: studentIds ?? null }, file)),
  broadcastBooks: (book: { title: string; author?: string; category?: string }, studentIds?: number[], file?: File | null) =>
    multipartPost('/teacher/broadcast/books', broadcastForm({ book, student_ids: studentIds ?? null }, file)),
};

// ----- SyllabusAI API clients (aliases over `endpoints` for named imports) -----
export const curriculumApi = endpoints.curriculum;
export const materialApi = endpoints.materials;
export const summaryApi = endpoints.summaries;
export const quizApi = endpoints.quizzes;
export const adminApi = endpoints.admin;
export const enrollmentApi = endpoints.enrollment;
