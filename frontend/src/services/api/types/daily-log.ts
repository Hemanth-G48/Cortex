// Daily log types.
// Extracted from services/api.ts (F8 split).

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
