// Endpoint client for this domain — extracted from services/api.ts (F8 split).

import { api, BASE, downloadAsFile } from '../core'
import { toIso } from '../../../utils/vaultDates'
import type { User } from '../types/user'
import type { AIChatResponse, AIClientModels, AICompleteRequest, AICompleteResponse, AIFlashcardsResponse, AIGradeAnswerResponse, AIHealth, AIInsightsResponse, AIProviderConfig, AIProviderTestResult, AIProviderType, AIProvidersResponse, AIQuizResponse, AIStudyPlanResponse, AISyllabusResponse } from '../types/ai'
import type { AnalyticsSummary, HeatmapDay, WeeklyFocus } from '../types/analytics'
import type { AcademicResource, Course, CourseContentResponse, CourseDocument, CourseGapsResponse, CourseResyncResult, CourseSyncResult, CourseSyncStatus, KbDomainDetail, KbDomainGapsResponse, KbDomainListResponse } from '../types/course'
import type { CurriculumUnit, Institution, Program, Subject } from '../types/curriculum'
import type { DailyLog, DailyLogStats } from '../types/daily-log'
import type { EnrollmentSummary } from '../types/enrollment'
import type { DietPlan, Exercise, Expense, ExpenseSummary, FitnessGoal, FitnessHubSummary, Membership, MuscleGroup, PersonalRecord, WeekActualsResponse, WeightGoal, Workout, WorkoutSplit } from '../types/fitness'
import type { DueFlashcard, Flashcard, FlashcardDeck, FlashcardSchedule, LeaderboardResponse } from '../types/flashcard'
import type { GapAnalysisResponse, GapGoalInfo, GapHistoryResponse } from '../types/gap'
import type { CalendarSyncEvent, ClassroomAssignmentsResponse, ClassroomCoursesResponse, GmailMessage, GmailUnread, GoogleConnectResponse, GoogleStatus } from '../types/google'
import type { CourseWeight, GPAResponse, Grade, GradeCalculateResult, NeededOnFinalResponse } from '../types/grade'
import type { Habit, HabitCalendarDay, HabitHeatmap, HabitLog, HabitStats, HabitTodayItem, HabitTrackerStatusWindow, HabitTrackerSummary, PomodoroSession } from '../types/habit'
import type { DailyNoteWriteResult, GlobalSearchResponse, KbAdaptation, KbAgentRun, KbAutoSubjectDetectResult, KbAutoSubjectPreview, KbAutomationJob, KbAutomationRunResult, KbChunk, KbCitation, KbConcept, KbConnectSuggestionsResponse, KbContextBundle, KbDailyNotes, KbDerivedGoal, KbDiffResponse, KbDocument, KbDocumentListResponse, KbDocumentTagsResponse, KbDomainsResponse, KbDuplicatesResponse, KbExplainResponse, KbFlashcardCandidate, KbFlashcardGenerateResult, KbForecast, KbGapsResponse, KbGoalItem, KbGraphResponse, KbHealth, KbJob, KbLinksResponse, KbMastery, KbMemoryItem, KbMemoryTimeline, KbMetadataUpdate, KbMindMapNode, KbMissingNoteSuggestion, KbObservabilityPayload, KbOutdatedNote, KbPersonalizedExplainResponse, KbPromptVersion, KbQualityItem, KbQualityResult, KbQualitySuggestion, KbRecommendItem, KbRecommendationItem, KbReflection, KbRelatedPaper, KbRelatedResponse, KbResearchExplainResult, KbScanResult, KbSearchEventItem, KbSearchMode, KbSearchResponse, KbSource, KbSourcePathValidation, KbSourceSyncResult, KbSourceSyncStatus, KbStats, KbSummaryResponse, KbUploadResult, KbVersion } from '../types/kb'
import type { LearningPlanDetail, LearningPlanSummary, LearningReverifyReport, LearningSchedule, LearningTask, PortswiggerSessionStatus } from '../types/learning'
import type { LifeArea } from '../types/life-area'
import type { LifePlannerEvent, LifePlannerSummary } from '../types/life-planner'
import type { Material, MaterialListResponse } from '../types/material'
import type { Quiz, QuizAnalytics, QuizAttemptResult, QuizHistoryItem } from '../types/quiz'
import type { Character, GamificationProfile, JournalEntry, Mission, MissionTask, MissionVaultTasksResponse, PriorityWindow, ProgressReport, Quest, QuestCentreBoard, QuestCentreCalendar, QuestCentreLifeArea, QuickActionsResponse, Reward, ScheduleEvent, StatusWindow } from '../types/rpg'
import type { StudyPlan, StudyPlanWeek } from '../types/study-plan'
import type { DependencyGraph, KbConceptGap, RoadmapItem, SubjectProfile, SubjectProfileStatus, TimeBudgetResponse, TopicItem, TopicOutcome, TopicStatus, UnitMatchCandidate, UserPreference } from '../types/subject'
import type { Summary, SummaryGenerateResponse } from '../types/summary'
import type { Assignment, EisenhowerMatrix, Exam, Goal, Note, Project, ProjectSummary, ProjectTask, QuickTask, Reminder, Task } from '../types/task'
import type { InterviewAnswerResponse, InterviewFinishResponse, InterviewSession, MistakeAnalysisResponse, MockAttemptItem, MockSubmitResponse, MockTestItem, PracticeAnswerResponse, PracticeGenerateResponse, PracticeQuestionItem, PracticeSessionResponse, SkillsExportResponse, SkillsResponse, TutorChatResponse, TutorDoubtResponse, TutorSessionItem } from '../types/tutor'
import type { DatabaseCounts, VaultCalendar, VaultSummary } from '../types/vault'
import type { BackupRestoreResult, FocusBoard, HealthAudit, MicroSession, PlanResyncReport, PlanSessionItem, PlanSessionState, SessionPomodoroResult, TodayOverview, TriageBulkResult, TriageQueueResponse, TriageStats, WeeklyReflectionResult, WeeklyReviewResponse } from '../types/workflow'

// ----- API endpoint helpers -----
export const endpoints = {
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
    // Defect #77 fix: persist a quiz attempt summary to the server (the
    // history page is the server truth; localStorage is only a cache).
    historyCreate: (d: { score: number; total_questions: number }) =>
      api.post<QuizHistoryItem | null>('/quizzes/history', d),
    analytics: () => api.get<QuizAnalytics>('/quizzes/analytics'),
  },
  enrollment: {
    summary: () => api.get<EnrollmentSummary>('/enrollment/summary'),
    update: (d: { institution_id: number; program_id: number }) =>
      api.put<{ user: User }>('/profile/enrollment', d),
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
    courses: () => api.get<ClassroomCoursesResponse>('/classroom/courses'),
    assignments: () => api.get<ClassroomAssignmentsResponse>('/classroom/assignments'),
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
    budget: () => api.get<{ today: number; limit: number; remaining: number }>('/ai/budget'),
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
    insights: (force = false) => api.post<AIInsightsResponse>('/ai/insights', { force }),
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
    syncKb: () => api.post<CourseSyncResult>('/courses/sync-kb'),
    syncStatus: () => api.get<CourseSyncStatus>('/courses/sync-status'),
    resources: () => api.get<AcademicResource[]>('/courses/resources'),
    documents: (id: number) => api.get<CourseDocument[]>(`/courses/${id}/documents`),
    // Subject Details page.
    content: (id: number) => api.get<CourseContentResponse>(`/courses/${id}/content`),
    // Saved per course: returns the stored analysis (cached) or computes it
    // once on first request. Use analyzeGaps to force a fresh computation.
    gaps: (id: number) => api.get<CourseGapsResponse>(`/courses/${id}/gaps`),
    analyzeGaps: (id: number) => api.post<CourseGapsResponse>(`/courses/${id}/gaps/analyze`),
    // Snapshot log of this subject's past gap analyses (oldest → newest).
    gapHistory: (id: number) => api.get<GapHistoryResponse>(`/courses/${id}/gaps/history`),
    resync: (id: number) => api.post<CourseResyncResult>(`/courses/${id}/resync`),
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
    create: (d: Partial<Exam>) => api.post<Exam>('/exams', d),
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
    delete: (id: number) => api.del<{ ok: boolean }>(`/habits/${id}`),      // Defect #49: archive with provenance (reason / triggering vault doc).
      archive: (id: number, d?: { reason?: string | null; document_id?: number | null }) =>
        api.post<Habit>(`/habits/${id}/archive`, d ?? {}),
    unarchive: (id: number) => api.post<Habit>(`/habits/${id}/unarchive`),
    setGoal: (habitId: number, goal: string) => api.put<Habit>(`/habits/${habitId}/goal`, { goal }),
    logs: (habitId: number) => api.get<HabitLog[]>(`/habits/${habitId}/logs`),
    stats: (habitId: number) => api.get<HabitStats>(`/habits/${habitId}/stats`),
    heatmap: (habitId: number) => api.get<HabitHeatmap>(`/habits/${habitId}/heatmap`),
    heatmaps: () => api.get<Record<string, HabitHeatmap>>('/habits/heatmaps'),
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
    // Per-day Weekly-Split actuals (defect #84).
    weekActuals: (weekStart?: string) =>
      api.get<WeekActualsResponse>(`/fitness/week-actuals${weekStart ? `?week_start=${weekStart}` : ''}`),
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
    update: (id: number, d: Partial<JournalEntry>) => api.put<JournalEntry>(`/journal-entries/${id}`, { ...d, user_id: 1 }),
    delete: (id: number) => api.del<{ ok: boolean }>(`/journal-entries/${id}`),
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
    summaries: () => api.get<Record<string, ProjectSummary>>('/projects/summaries'),
    tasks: (id: number) => api.get<ProjectTask[]>(`/projects/${id}/tasks`),
    createTask: (d: Partial<ProjectTask>) => api.post<ProjectTask>('/project-tasks', d),
    updateTask: (id: number, d: Partial<ProjectTask>) => api.put<ProjectTask>(`/project-tasks/${id}`, d),
    deleteTask: (id: number) => api.del<{ ok: boolean }>(`/project-tasks/${id}`),
  },
  lifeAreas: {
    list: () => api.get<LifeArea[]>('/life-areas'),
    create: (d: Partial<LifeArea>) => api.post<LifeArea>('/life-areas', d),
    update: (id: number, d: Partial<LifeArea>) => api.put<LifeArea>(`/life-areas/${id}`, d),
    delete: (id: number) => api.del<{ ok: boolean }>(`/life-areas/${id}`),
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
    // Authoritative quest/mission counts + shared XP wallet (defects #87, #88).
    board: () => api.get<QuestCentreBoard>('/quest-centre/board'),
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
    // Vault-derived subtask suggestions (defect #80).
    vaultTasks: (id: number, limit = 8) =>
      api.get<MissionVaultTasksResponse>(`/missions/${id}/vault-tasks?limit=${limit}`),
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
      create: (d: { name: string; source_type?: string; root_path: string; enabled?: boolean; sync_type?: string; sync_source_path?: string }) =>
        api.post<KbSource>('/kb/sources', d),
      update: (id: number, d: { name?: string; source_type?: string; root_path?: string; enabled?: boolean; sync_type?: string; sync_source_path?: string }) =>
        api.put<KbSource>(`/kb/sources/${id}`, d),
      remove: (id: number) => api.del<{ ok: boolean; deleted_documents: number }>(`/kb/sources/${id}`),
      // ``path`` (optional) scopes the scan to one folder inside the source
      // root — the manual "update from folder" action.
      scan: (id: number, path?: string) =>
        api.post<KbScanResult>(`/kb/sources/${id}/scan${path ? `?path=${encodeURIComponent(path)}` : ''}`),
      // Phase 9 (Idea 89): external repo sync.
      sync: (id: number) => api.post<KbSourceSyncResult>(`/kb/sources/${id}/sync`),
      syncStatus: (id: number) => api.get<KbSourceSyncStatus>(`/kb/sources/${id}/sync-status`),
      // Defect #20: pre-flight validation of a candidate root path so the UI
      // can hint before the create call is made.
      validate: (path: string) =>
        api.get<KbSourcePathValidation>(`/kb/sources/validate?path=${encodeURIComponent(path)}`),
    },
    folders: {
      // Canonical Second Brain folder/domain hierarchy (source of truth).
      tree: (courseId: number) => api.get<KbDomainListResponse>(`/kb/folders?course_id=${courseId}`),
      get: (folderId: number) => api.get<KbDomainDetail>(`/kb/folders/${folderId}`),
      // Persisted domain gap analysis: saved copy (cached) or first compute.
      gaps: (folderId: number) => api.get<KbDomainGapsResponse>(`/kb/folders/${folderId}/gaps`),
      // Explicit Re-analyze — the only path that recomputes on demand.
      analyzeGaps: (folderId: number) => api.post<KbDomainGapsResponse>(`/kb/folders/${folderId}/gaps/analyze`),
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
    // Flat top-level domain list with live doc counts (defect #83).
    domains: () => api.get<KbDomainsResponse>('/kb/domains'),
    // Vault mastery read model (defects #40, #71, #76, #82, #96): competency
    // derived from LearningEvent practice logs, per subject or whole vault.
    mastery: (params?: { subject?: number; subject_name?: string; days?: number }) => {
      const qs = new URLSearchParams();
      if (params?.subject !== undefined) qs.set('subject', String(params.subject));
      if (params?.subject_name) qs.set('subject_name', params.subject_name);
      if (params?.days !== undefined) qs.set('days', String(params.days));
      const q = qs.toString();
      return api.get<KbMastery>(`/kb/mastery${q ? `?${q}` : ''}`);
    },
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
      // Explicit user action — re-runs the AI (or fallback) tag proposal and
      // persists it. The GET endpoint only reads persisted suggestions, so
      // opening a document never spends a model call.
      propose: (documentId: number) =>
        api.post<KbDocumentTagsResponse>(`/kb/documents/${documentId}/tags/propose`),
      apply: (documentId: number, tagIds: number[]) =>
        api.post<KbDocumentTagsResponse>(`/kb/documents/${documentId}/tags`, {
          document_id: documentId,
          tag_ids: tagIds,
        }),
      create: (documentId: number, name: string) =>
        api.post<KbDocumentTagsResponse>(`/kb/documents/${documentId}/tags/create`, { name }),
      reject: (documentId: number, tagId: number) =>
        api.del<{ ok: boolean; removed: number }>(`/kb/documents/${documentId}/tags/${tagId}`),
    },
    // Auto-detected course subjects from vault documents (defect #27).
    autoSubjects: {
      preview: (sampleSize = 100) =>
        api.get<KbAutoSubjectPreview>(`/kb/auto-subjects/preview?sample_size=${sampleSize}`),
      detect: (dryRun = false, limit = 0) =>
        api.post<KbAutoSubjectDetectResult>(
          `/kb/auto-subjects/detect?dry_run=${dryRun}&limit=${limit}`,
        ),
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
      // Redesigned actionable gap analysis (goals + domains).
      domains: () => api.get<{ goals: GapGoalInfo[] }>('/kb/gaps/domains'),
      goal: (goal: string) => api.get<GapAnalysisResponse>(`/kb/gaps/goal?goal=${encodeURIComponent(goal)}`),
      // Explicit recompute — the only path that refreshes a saved analysis.
      analyzeGoal: (goal: string) => api.post<GapAnalysisResponse>(`/kb/gaps/goal/analyze?goal=${encodeURIComponent(goal)}`),
      // Snapshot log of this goal's past gap analyses (oldest → newest).
      goalHistory: (goal: string) => api.get<GapHistoryResponse>(`/kb/gaps/goal/history?goal=${encodeURIComponent(goal)}`),
      // Draft a ready-to-edit capture note for one gap (idempotent).
      createNote: (d: {
        name: string;
        subject?: string | null;
        why?: string | null;
        learn?: string[];
        practice?: string[];
        sources?: { document_id: number; title?: string | null }[];
      }) => api.post<{ document: { id: number; title: string; status: string }; created: boolean }>('/kb/gaps/note', d),
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
      // Defect #66: echo a completed task into today's vault daily note.
      completeTask: (d: { title: string; task_id?: number | null; source?: string | null }) =>
        api.post<DailyNoteWriteResult>('/kb/daily-notes/complete-task', d),
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
    // Auto-link pass + review queue (defect #74).
    links: {
      queue: () => api.get<{ items: Record<string, unknown>[] }>('/kb/links/queue'),
      auto: (limit?: number) =>
        api.post<{ ok: boolean; summary: Record<string, unknown>; queue: Record<string, unknown>[] }>(
          '/kb/links/auto',
          limit !== undefined ? { limit } : {},
        ),
      accept: (edgeIds: number[]) =>
        api.post<{ ok: boolean; accepted: number }>('/kb/links/accept', { edge_ids: edgeIds }),
      reject: (edgeIds: number[]) =>
        api.post<{ ok: boolean; rejected: number }>('/kb/links/reject', { edge_ids: edgeIds }),
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
      // Defect #75: the status filter is applied server-side.
      list: (status?: string) =>
        api.get<{ items: MockTestItem[] }>(`/kb/mocks${status ? `?status=${status}` : ''}`),
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
      // Defect #52: write a reflection line into today's vault daily note.
      create: (d: { content: string; kind?: string | null }) =>
        api.post<DailyNoteWriteResult>('/kb/reflections', d),
      generate: () => api.post<KbReflection>('/kb/reflections/generate', {}),
      adjust: () => api.post<{ applied: unknown[]; count: number }>('/kb/reflections/adjust'),
      derivedGoals: () => api.get<{ items: KbDerivedGoal[] }>('/kb/goals/derived'),
      confirmGoal: (d: KbDerivedGoal) => api.post<{ ok: boolean; goal_id: number }>('/kb/goals/derived/confirm', d),
      goals: () => api.get<{ items: KbGoalItem[] }>('/kb/goals'),
      goalProgress: (goalId: number) => api.get<{ goal_id: number; title: string; progress_percentage: number; topics_mastered: number; topics_total: number }>(`/kb/goals/${goalId}/progress`),
    },
    today: {
      overview: (date?: string) => api.get<TodayOverview>(`/kb/today${date ? `?date=${encodeURIComponent(date)}` : ''}`),
    },
    triage: {
      list: (limit = 50) => api.get<TriageQueueResponse>(`/kb/triage?limit=${limit}`),
      stats: () => api.get<TriageStats>('/kb/triage/stats'),
      applySubjects: (documentId: number) =>
        api.post<{ ok: boolean; subjects_applied: number; subjects: string[] }>(`/kb/triage/${documentId}/apply-subjects`),
      tag: (documentId: number, name: string) =>
        api.post<{ ok: boolean; applied: number }>(`/kb/triage/${documentId}/tag`, { name }),
      dismiss: (documentId: number) =>
        api.post<{ ok: boolean }>(`/kb/triage/${documentId}/dismiss`),
      acceptAll: (limit = 200) => api.post<TriageBulkResult>(`/kb/triage/accept-all?limit=${limit}`),
      dismissAll: (limit = 200) => api.post<TriageBulkResult>(`/kb/triage/dismiss-all?limit=${limit}`),
    },
    backup: {
      export: () => downloadAsFile(`${BASE}/kb/backup/export`, `vault-backup-${new Date().toISOString().slice(0, 10)}.zip`),
      restore: (file: File, replaceDb = false) => {
        const form = new FormData();
        form.append('file', file);
        return fetch(`${BASE}/kb/backup/restore${replaceDb ? '?replace_db=true' : ''}`, {
          method: 'POST',
          body: form,
        }).then((res) => {
          if (!res.ok) return res.json().then((b) => Promise.reject(new Error(b?.detail ?? b?.error ?? `Restore ${res.status}`)));
          return res.json() as Promise<BackupRestoreResult>;
        });
      },
    },
    weeklyReview: {
      overview: () => api.get<WeeklyReviewResponse>('/kb/weekly-review'),
      generateReflection: (regenerate = false) =>
        api.post<WeeklyReflectionResult>('/kb/weekly-review/generate-reflection', { regenerate }),
      confirmGoal: (d: { title: string; subject_id: number; quarter?: string; year?: number | null; target_date?: string | null; roadmap_id?: number | null }) =>
        api.post<{ ok: boolean; goal_id: number }>('/kb/weekly-review/goals/confirm', d),
    },
    learningPlans: {
      create: (d: {
        goal: string;
        description?: string | null;
        resources: { label?: string | null; url?: string | null }[];
        known?: string[];
        unknown?: string[];
        goal_key?: string | null;
      }) => api.post<{ plan: LearningPlanDetail }>('/kb/learning-plans', d),
      // Layer 1 only: crawl the supplied URL and persist the real platform
      // structure (paths → resources) without generating a roadmap.
      discover: (d: {
        goal: string;
        description?: string | null;
        resources: { label?: string | null; url?: string | null }[];
        known?: string[];
        unknown?: string[];
        goal_key?: string | null;
      }) => api.post<{ plan: LearningPlanDetail }>('/kb/learning-plans/discover', d),
      // Layer 2 (explicit user action): build the personalised roadmap on top
      // of the persisted source structure.
      generate: (planId: number, d?: { known?: string[]; unknown?: string[] }) =>
        api.post<{ plan: LearningPlanDetail }>(`/kb/learning-plans/${planId}/generate`, d ?? {}),
      list: () => api.get<{ items: LearningPlanSummary[] }>('/kb/learning-plans'),
      get: (planId: number) => api.get<{ plan: LearningPlanDetail }>(`/kb/learning-plans/${planId}`),
      toggleTask: (planId: number, taskId: number, done: boolean) =>
        api.post<{ ok: boolean; task: LearningTask }>(`/kb/learning-plans/${planId}/tasks/${taskId}/toggle`, { done }),
      remove: (planId: number) => api.del<{ ok: boolean }>(`/kb/learning-plans/${planId}`),
      // PortSwigger sign-in: lets the crawler verify auth-gated resource URLs.
      session: {
        status: () => api.get<{ session: PortswiggerSessionStatus }>('/kb/learning-plans/session'),
        login: (d: { email: string; password: string; remember?: boolean }) =>
          api.post<{ session: PortswiggerSessionStatus }>('/kb/learning-plans/session/login', d),
        logout: (d?: { clear_credentials?: boolean }) =>
          api.post<{ session: PortswiggerSessionStatus }>('/kb/learning-plans/session/logout', d ?? {}),
      },
      reverify: (planId: number) =>
        api.post<{ plan: LearningPlanDetail; reverify: LearningReverifyReport }>(`/kb/learning-plans/${planId}/reverify`),
      // Study-Session Loop: read-only state + explicit start/complete.
      // (Distinct from ``session`` above, which is the PortSwigger sign-in.)
      planSession: {
        state: (planId: number) => api.get<{ session: PlanSessionState }>(`/kb/learning-plans/${planId}/session`),
        // ``task_id`` starts the session on a specific roadmap task (e.g. the
        // first incomplete task of a scheduled study day).
        start: (planId: number, d?: { duration_mins?: number; task_id?: number }) =>
          api.post<{ ok: boolean; session: PlanSessionItem; state: PlanSessionState }>(
            `/kb/learning-plans/${planId}/session/start`,
            d ?? {},
          ),
        complete: (planId: number, sessionId: number) =>
          api.post<{
            ok: boolean;
            session: PlanSessionItem;
            task_completed: boolean;
            // Full fresh state (matches PlanSessionState, with live_session null).
            plan_id: number;
            live_session: PlanSessionItem | null;
            last_session: PlanSessionItem | null;
            next_task: LearningTask | null;
            progress: { total_tasks: number; done_tasks: number; progress_percent: number };
            completed: boolean;
          }>(`/kb/learning-plans/${planId}/session/${sessionId}/complete`),
      },
      // Plan Re-sync (explicit): refresh Layer 1 — new paths added, removed
      // ones flagged; the personalised roadmap is left untouched.
      resync: (planId: number) =>
        api.post<{ plan: LearningPlanDetail; resync: PlanResyncReport }>(`/kb/learning-plans/${planId}/resync`),
      // Study Schedule — roadmap → day-by-day plan. Building is an explicit
      // user action; reading is read-only and never calls the LLM.
      schedule: {
        get: (planId: number) =>
          api.get<{ schedule: LearningSchedule | null }>(`/kb/learning-plans/${planId}/schedule`),
        create: (planId: number, d: {
          mode: string;
          daily_hours?: number | null;
          modules_per_day?: number | null;
          time_slots?: string[];
          instruction?: string | null;
        }) => api.post<{ schedule: LearningSchedule }>(`/kb/learning-plans/${planId}/schedule`, d),
        remove: (planId: number) =>
          api.del<{ ok: boolean }>(`/kb/learning-plans/${planId}/schedule`),
      },
    },
    // Vault Health Audit: read-only aggregate + explicit dismiss/resolve actions.
    healthAudit: {
      audit: (limit = 12) => api.get<HealthAudit>(`/kb/health-audit?limit=${limit}`),
      rescan: () => api.post<{ ok: boolean; created_outdated: number; health_score: number }>('/kb/health-audit/rescan'),
      dismissMissing: (suggestionId: number) =>
        api.post<{ id: number; status: string }>(`/kb/health-audit/missing/${suggestionId}/dismiss`),
      resolveOutdated: (noteId: number, action: 'updated' | 'archived' | 'dismissed') =>
        api.post<{ id: number; document_id: number; status: string }>(`/kb/health-audit/outdated/${noteId}/resolve`, { action }),
      archiveDuplicate: (documentId: number) =>
        api.post<{ ok: boolean }>(`/kb/health-audit/duplicates/${documentId}/archive`),
    },
    // Focus/Readiness Loop: read-only board + explicit session start.
    focus: {
      board: (limit = 5) => api.get<FocusBoard>(`/kb/focus?limit=${limit}`),
      start: (topicId: number, durationMins?: number) =>
        api.post<{ ok: boolean; session: MicroSession }>('/kb/focus/start', {
          topic_id: topicId,
          ...(durationMins ? { duration_mins: durationMins } : {}),
        }),
    },
    sessions: {
      start: (topicId: number, durationMins?: number) =>
        api.post<{ session: MicroSession }>('/sessions/start', {
          topic_id: topicId,
          ...(durationMins ? { duration_mins: durationMins } : {}),
        }),
      complete: (sessionId: number) =>
        api.post<{ ok: boolean; session: MicroSession }>(`/sessions/${sessionId}/complete`),
      pomodoro: (sessionId: number) =>
        api.post<SessionPomodoroResult>(`/sessions/${sessionId}/pomodoro`),
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

