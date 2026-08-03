import { WeekGrid } from './WeekGrid';
import { mapLogs, toIso, type LogEntry } from '../../utils/vaultDates';
import type { Habit } from '../../services/api';

const ACCENT: Record<string, string> = {
  blue: 'var(--habit-blue)',
  green: 'var(--habit-green)',
  orange: 'var(--habit-orange)',
  red: 'var(--habit-red)',
};

interface HabitStreakCardProps {
  habit: Habit;
  logs: LogEntry[];
  /** Log today's habit (called with the habit id). */
  onLog: (habitId: number) => void;
  /** Toggle today's completion state. */
  onToggleToday: (habitId: number) => void;
}

/** Streak card: 4-week check grid, completion %, streak badge, "Completed Today" checkbox. */
export const HabitStreakCard = ({ habit, logs, onLog, onToggleToday }: HabitStreakCardProps) => {
  const color = ACCENT[habit.color_theme] ?? 'var(--habit-blue)';
  const byDate = mapLogs(logs);
  const todayIso = toIso(new Date());
  const todayLog = byDate.get(todayIso);
  const completedToday = !!todayLog?.completed;

  const gridDays = 28;
  const loggedDays = logs.filter((l) => l.completed).length;
  const percent = Math.min(100, Math.round((loggedDays / gridDays) * 100));

  return (
    <div className="vault-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div>
          <div className="vault-body" style={{ fontWeight: 600 }}>{habit.name}</div>
          <div className="vault-muted">{percent}% completion (last 4 weeks)</div>
        </div>
        <span
          style={{
            background: color,
            color: '#fff',
            borderRadius: 6,
            padding: '2px 8px',
            fontSize: 12,
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          Streak: {habit.current_streak} day{habit.current_streak === 1 ? '' : 's'}
        </span>
      </div>

      <div style={{ marginTop: 12 }}>
        <WeekGrid logs={logs} color={color} weeks={4} />
      </div>

      <label
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginTop: 12,
          cursor: 'pointer',
          fontSize: 13,
          color: 'var(--vault-text-primary)',
        }}
      >
        <input
          type="checkbox"
          checked={completedToday}
          onChange={() => {
            if (completedToday) onToggleToday(habit.id);
            else onLog(habit.id);
          }}
        />
        Completed Today
      </label>
    </div>
  );
};
