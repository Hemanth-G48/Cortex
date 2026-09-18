// Gamification / Quest Centre types.
// Extracted from services/api.ts (F8 split).

import type { LifeArea } from './life-area'

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

export interface Character {
  id: number; user_id: number; name: string;
  class_name: string; level: number; xp: number;
  strength: number; agility: number; intelligence: number; endurance: number;
  current_quests: number; created_at: string | null; updated_at: string | null;
}

/** Authoritative quest/mission counts (audit defects #87, #88). */
export interface QuestCentreBoardCounts {
  total: number;
  by_status: Record<string, number>;
  completed: number;
  open: number;
  done_statuses: string;
}

export interface QuestCentreBoard {
  quests: QuestCentreBoardCounts;
  missions: QuestCentreBoardCounts;
  characters: { total_xp: number; level: number };
}

export interface AddXpRequest {
  amount: number;
}

/** Vault-derived mission subtask suggestions (audit defect #80). */
export interface MissionVaultTaskSuggestion {
  title: string;
  kind: 'checklist' | 'outline' | 'bullet';
  document_id: number;
  document_title: string | null;
}

export interface MissionVaultTasksResponse {
  query: string;
  suggestions: MissionVaultTaskSuggestion[];
  documents: { id: number; title: string }[];
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
