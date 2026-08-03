import { useMemo, useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { HtTabs } from './HtTabs';
import { HtBadHabitCard } from './HtBadHabitCard';
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
 * Row-3 daily bad habits (Phases 77-84): accountability row — admit the slip,
 * take the -XP hit, sorted by days_caught desc.
 */
export const HtDailyBadHabits = ({ habits, todayItems, overviewDays, onChanged }: Props) => {
  const { toast } = useToast();
  const [tab, setTab] = useState('all');
  const [busy, setBusy] = useState<number | null>(null);

  const loggedToday = useMemo(
    () => new Set(todayItems.filter((i) => i.log_today).map((i) => i.id)),
    [todayItems],
  );
  const sorted = useMemo(
    () => [...habits].sort((a, b) => b.days_caught - a.days_caught),
    [habits],
  );
  const visible = tab === 'today' ? sorted.filter((h) => loggedToday.has(h.id)) : sorted;

  const admit = async (habit: Habit) => {
    if (busy === habit.id) return;
    setBusy(habit.id);
    try {
      const log = await endpoints.habits.logHabit(habit.id);
      toast(`${habit.name} — honest! ${log.xp_change} XP 🔴`, 'warning');
      onChanged();
    } catch {
      toast('Could not log habit', 'error');
    } finally {
      setBusy(null);
    }
  };

  const overview = useMemo(() => {
    const logs = overviewDays.flatMap((d) => d.logs);
    const xpLost = logs.reduce((s, l) => s + Math.abs(Math.min(l.xp_change, 0)), 0);
    const caughtByHabit = new Map<string, number>();
    for (const l of logs) caughtByHabit.set(l.habit_name, (caughtByHabit.get(l.habit_name) ?? 0) + 1);
    const worst = [...caughtByHabit.entries()].sort((a, b) => b[1] - a[1])[0];
    return {
      caught: logs.length,
      xpLost,
      worstOffender: worst ? `${worst[0]} (${worst[1]}x)` : '—',
      cleanToday: !todayItems.some((i) => i.log_today && i.habit_type === 'bad'),
    };
  }, [overviewDays, todayItems]);

  return (
    <div className="ht-row">
      <div className="ht-row-header">
        <div className="ht-row-title"><span className="ht-row-emoji">⚠️</span>Daily Bad Habits</div>
        <HtTabs tabs={TABS} activeTab={tab} onChange={setTab} ariaLabel="Filter bad habits" />
      </div>

      {tab === 'overview' ? (
        <div className="ht-overview">
          <div className="ht-ov-stat">
            <div className="ov-label">Caught This Week</div>
            <div className="ov-value bad">{overview.caught} 📉</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">XP Lost</div>
            <div className="ov-value bad">-{overview.xpLost}</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">Worst Offender</div>
            <div className="ov-value" style={{ fontSize: '0.9rem' }}>{overview.worstOffender}</div>
          </div>
          <div className="ht-ov-stat">
            <div className="ov-label">Today</div>
            <div className="ov-value" style={{ color: overview.cleanToday ? 'var(--ht-good)' : 'var(--ht-bad)' }}>
              {overview.cleanToday ? 'Clean ✅' : 'Slipped ⚠️'}
            </div>
          </div>
        </div>
      ) : visible.length === 0 ? (
        <div className="ht-empty-pixel">
          <span className="ht-empty-icon" aria-hidden="true">{tab === 'today' ? '🛡️' : '⚠️'}</span>
          <span className="ht-empty-title">{tab === 'today' ? 'Clean today!' : 'No bad habits tracked'}</span>
          <span className="ht-empty-sub">
            {tab === 'today' ? 'No slips admitted today — keep the streak clean! 💪' : 'Add a bad habit from Quick Actions to hold yourself accountable.'}
          </span>
        </div>
      ) : (
        <div className="ht-habit-scroll">
          {visible.map((h) => (
            <HtBadHabitCard
              key={h.id}
              habit={h}
              loggedToday={loggedToday.has(h.id)}
              busy={busy === h.id}
              onAdmit={admit}
            />
          ))}
        </div>
      )}
    </div>
  );
};
