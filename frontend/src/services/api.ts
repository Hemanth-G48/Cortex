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
export interface AIHealth {
  available: boolean;
  mode: string;
  model: string | null;
  models: string[];
}

export interface AIClientModels {
  models: string[];
  enabled: boolean;
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

// ----- API endpoint helpers -----
export const endpoints = {
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
};

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
  get: () => api.get<{ content: string | null }>('/braindumps'),
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
