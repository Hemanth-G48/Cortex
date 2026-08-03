import { HeatmapGrid } from './HeatmapGrid';
import type { LogEntry } from '../../utils/vaultDates';
import type { Habit } from '../../services/api';

const ACCENT: Record<string, string> = {
  blue: 'var(--habit-blue)',
  green: 'var(--habit-green)',
  orange: 'var(--habit-orange)',
  red: 'var(--habit-red)',
};

interface HabitHeatmapCardProps {
  habit: Habit;
  /** Log entries for the past month. */
  days: LogEntry[];
  /** Mark today complete. */
  onComplete: (habitId: number) => void;
}

/** Heatmap card: 7x7 past-month grid, habit title, "Today is {date}", mark-complete button. */
export const HabitHeatmapCard = ({ habit, days, onComplete }: HabitHeatmapCardProps) => {
  const color = ACCENT[habit.color_theme] ?? 'var(--habit-blue)';
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });

  return (
    <div className="vault-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <div>
          <div className="vault-body" style={{ fontWeight: 600 }}>{habit.name}</div>
          <div className="vault-muted">Today is {today}</div>
        </div>
        <button
          className="btn-complete"
          onClick={() => onComplete(habit.id)}
          style={{ border: `1px solid ${color}`, color }}
        >
          Mark as complete
        </button>
      </div>

      <div style={{ marginTop: 12 }}>
        <HeatmapGrid logs={days} color={color} monthLabel="Last 30 days" />
      </div>
    </div>
  );
};
