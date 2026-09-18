// Analytics summary types.
// Extracted from services/api.ts (F8 split).

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
