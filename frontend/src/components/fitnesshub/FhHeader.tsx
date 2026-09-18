interface FhHeaderProps {
  workoutCount: number;
  totalCalories: number;
  activePlans: number;
  /** Shared XP wallet from the Quest Centre board (defect #87). */
  level?: number | null;
  totalXp?: number | null;
}

/** Fitness Hub header (Phase 59): full-width banner, ~28px title, stat chips. */
export const FhHeader = ({ workoutCount, totalCalories, activePlans, level, totalXp }: FhHeaderProps) => (
  <header className="fh-header">
    <span className="fh-header-eyebrow">🏋️ Student OS · Fitness Module</span>
    <h1>Fitness-Hub</h1>
    <p className="fh-header-sub">
      Track your splits, habits, muscle groups, expenses and exercises — everything
      in one fixed-sidebar dashboard. Stay consistent, get strong.
    </p>
    <div className="fh-header-chips">
      <span className="fh-chip">💪 Workouts <b>{workoutCount}</b></span>
      <span className="fh-chip">🔥 Calories <b>{totalCalories.toLocaleString()}</b></span>
      <span className="fh-chip">🍽️ Active Plans <b>{activePlans}</b></span>
      {totalXp != null && (
        <span className="fh-chip">✨ Level {level ?? 1} · XP <b>{totalXp.toLocaleString()}</b></span>
      )}
    </div>
  </header>
);
