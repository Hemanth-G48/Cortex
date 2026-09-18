// Habit + pomodoro types.
// Extracted from services/api.ts (F8 split).

import type { Reward } from './rpg'

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
  // Archive provenance (defect #49).
  archived_reason?: string | null;
  archived_document_id?: number | null;
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
