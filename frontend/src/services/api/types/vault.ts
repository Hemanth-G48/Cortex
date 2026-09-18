// Vault summary + calendar types.
// Extracted from services/api.ts (F8 split).

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
