export type Priority = 'High' | 'Medium' | 'Low';
export type Status = 'Not started' | 'In progress' | 'Completed';
export type QuestCategory = 'Work' | 'Fitness' | 'Personal' | 'Learning' | 'Social' | 'Health';

// Quest Centre / gamification types (re-exported from the API client so
// components import from one place).
export type {
  GamificationProfile,
  StatusWindow,
  StatusWindowCharacter,
  TodayTask,
  ProgressReport,
  PriorityWindow,
  PriorityWindowItem,
  QuickAction,
  CalendarQuest,
  QuestDateGroup,
  QuestCentreCalendar,
  QuestCentreLifeArea,
} from '../services/api';
export type { LifeArea, Mission, User, UserRole, AuthUser } from '../services/api';
export type {
  Book, BookCategory, BookInsights, BookListResponse,
  BrainDump,
  DailyCategory, EnergyLevel, DailyScheduleItem, DailyScheduleStats,
  AppNotification,
  TeacherStudent, TeacherStudentStats, TeacherStudentDetail, TeacherBroadcastResult,
} from '../services/api';
export { getToken, setToken, clearToken, authApi, uploadApi } from '../services/api';
export { bookApi, brainDumpApi, dailyScheduleApi, notificationApi, teacherApi } from '../services/api';
// SyllabusAI
export type {
  Institution, Program, Subject, CurriculumUnit,
  Material, MaterialListResponse,
  Summary,
  Quiz, QuizQuestion, QuizAttemptResult, QuizAttemptResultItem, QuizHistoryItem, QuizAnalytics,
  EnrollmentSummary,
} from '../services/api';
export {
  curriculumApi, materialApi, summaryApi, quizApi, adminApi, enrollmentApi,
} from '../services/api';
