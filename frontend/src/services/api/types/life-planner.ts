// Life planner types.
// Extracted from services/api.ts (F8 split).

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
