// Fitness hub types.
// Extracted from services/api.ts (F8 split).

export interface Workout {
  id: number; user_id: number; date: string;
  type: string; duration_minutes: number;
  calories: number | null; notes: string | null;
}

export interface FitnessGoal {
  id: number; user_id: number; name: string;
  target: number; current: number; unit: string | null;
}

// ----- Fitness Hub types (99-phase plan, Phases 43-48) -----
export interface Exercise {
  id: number; name: string; muscle_group_id: number | null;
  sets: number; reps: number; weight: number; user_id: number;
}

export interface MuscleGroup {
  id: number; name: string; body_part: string;
  image_3d_url: string | null; sort_order: number; user_id: number;
}

export interface MuscleGroupOverview extends MuscleGroup {
  exercise_count: number;
}

export interface WorkoutSplit {
  id: number; day_of_week: number; split_name: string;
  exercise_list: string | null; week_number: number; user_id: number;
}

export interface SplitDay {
  day: string; day_of_week: number;
  split_name: string; exercises: string[];
}

/** Per-day Weekly-Split actuals (audit defect #84). */
export interface WeekActualDay {
  day: string;
  day_of_week: number;
  date: string;
  workouts: { id: number; type: string; duration_minutes: number; calories: number | null }[];
  total_minutes: number;
  logged: boolean;
  vault_mentions: boolean;
}

export interface WeekActualsResponse {
  week_start: string;
  days: WeekActualDay[];
}

export interface Expense {
  id: number; title: string; cost: number;
  date: string; category: string; user_id: number;
}

export interface ExpenseSummary {
  total: number;
  by_category: Record<string, number>;
}

export interface PersonalRecord {
  id: number; exercise_name: string;
  current_weight: number; target_weight: number;
  unit: string; user_id: number;
  // computed by pr_summary helper
  percent?: number;
}

export interface DietPlan {
  id: number; title: string; is_active: boolean;
  sort_order: number; user_id: number;
}

export interface WeightGoal {
  initial: number | null; current: number | null;
  target: number | null; percent: number;
}

export interface Membership {
  membership_status: string;
  next_payment_date: string | null;
  days_to_payment: number | null;
}

export interface SpecHabitHeatmap {
  id: number; name: string; goal: string | null;
  days_completed: number; percent: number;
  heatmap_7x7: { date: string; completed: boolean; count: number }[];
}

export interface FitnessHubSummary {
  weight_goal: WeightGoal | null;
  pr_tracker: PersonalRecord[];
  membership: Membership | null;
  diet_plans: DietPlan[];
  expenses_summary: ExpenseSummary;
  weekly_split: { 1: SplitDay[]; 2: SplitDay[] };
  muscle_groups: MuscleGroupOverview[];
  spec_habits: SpecHabitHeatmap[];
}
