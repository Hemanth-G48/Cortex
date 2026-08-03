import { useMemo, useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { HtTabs } from './HtTabs';
import { HtGoodHabitCard } from './HtGoodHabitCard';
import type { Habit, HabitCalendarDay, HabitTodayItem } from '../../services/api';

interface Props {
  habits: Habit[];
  todayItems: HabitTodayItem[];
  overviewDays: HabitCalendarDay[];
  onChanged: () => void;
}

const TABS = [
  { id: 'all', label: 'All' },
  { id: 'today', label: 'Did Today' },
  { id: 'overview', label: 'Overview' },
];

/**
 * Row-2 daily good habits (Phases 69-76): horizontal card row + All /
 * Did Today / Overview tabs, dopamine ordering by streak desc.
 */
export const HtDailyGoodHabits = ({ habits, todayItems, overviewDays, onChanged }: Props) => {
  const { toast } = useToast();
  const [tab, setTab] = useState('all');
  const [busy, setBusy] = useState<number | null>(null);

  const loggedToday = useMemo(
    () => new Set(todayItems.filter((i) => i.log_today).map((i) => i.id)),
    [todayItems],
  );
  const sorted = useMemo(
    () => [...habits].sort((a, b) => b.current_streak - a.current_streak),
    [habits],
  );
  const visible = tab === 'today' ? sorted.filter((h) => loggedToday.has(h.id)) : sorted;

  const complete = async (habit: Habit) => {
    if (busy === habit.id) return;
    setBusy(habit.id);
    try {
      const log = await endpoints.habits.logHabit(habit.id);
      toast(`${habit.name} done! +${log.xp_change} XP 🟢`, 'success');
      onChanged();
    } catch {
      toast('Could not log habit', 'error');
    } finally {
      setBusy(null);
    }
  };

  // Overview aggregates (Phase 73): this week's completions + XP + streaks.
  const overview = useMemo(() => {
    const logs = overviewDays.flatMap((d) => d.logs);
    const xpEarned = logs.reduce((s, l) => s + Math.max(l.xp_change, 0), 0);
    return {
      completions: logs.length,
      xpEarned,
      bestStreak: habits.reduce((m, h) => Math.max(m, h.current_streak), 0),
      mostConsistent: [...habits].sort((a, b) => b.longest_streak - a.longest_streak)[0]?.name ?? '—',
    };
  }, [overviewDays, habits]);

  return (
    <div className="ht-row">
      <div className="ht-row-header">
        <div className="ht-row-title"><span className="ht-row-emoji">🌱</span>Daily Good Habits</div>
        <HtTabs tabs={TABS} activeTab={tab} onChange={setTab} ariaLabel="Filter good habits" />
      </div>

      {tab === 'overview' ? (
        <div className="ht-overview">
          <div className="ht-ov-stat">
            <div className="ov-label">This Week</div>
            <div className="ov-value good">{overview.completions} ✅</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">XP Earned</div>
            <div className="ov-value good">+{overview.xpEarned}</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">Best Streak</div>
            <div className="ov-value">🔥 {overview.bestStreak}d</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">Most Consistent</div>
            <div className="ov-value" style={{ fontSize: '0.9rem' }}>{overview.mostConsistent}</div>
          </div>
        </div>
      ) : visible.length === 0 ? (
        <div className="ht-empty-pixel">
          <span className="ht-empty-icon" aria-hidden="true">{tab === 'today' ? '🌱' : '➕'}</span>
          <span className="ht-empty-title">{tab === 'today' ? 'Nothing completed today' : 'No good habits yet'}</span>
          <span className="ht-empty-sub">
            {tab === 'today' ? 'Go earn some gold — complete a good habit! 💪' : 'Create one from Quick Actions to start earning XP.'}
          </span>
        </div>
      ) : (
        <div className="ht-habit-scroll">
          {visible.map((h) => (
            <HtGoodHabitCard
              key={h.id}
              habit={h}
              loggedToday={loggedToday.has(h.id)}
              busy={busy === h.id}
              onComplete={complete}
            />
          ))}
        </div>
      )}
    </div>
  );
};
