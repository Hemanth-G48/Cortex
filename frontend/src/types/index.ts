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
export type { LifeArea, Mission, User } from '../services/api';
