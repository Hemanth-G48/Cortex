// Life area types.
// Extracted from services/api.ts (F8 split).

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
