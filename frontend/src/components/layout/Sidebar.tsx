import { useEffect, useState } from 'react';
import { NavLinks } from '../widgets/NavLinks';
import { ThemeSwitcher } from '../shared/ThemeSwitcher';
import { DigitalClock } from '../widgets/DigitalClock';
import { ProgressBars } from '../widgets/ProgressBars';
import { QuickActions } from '../widgets/QuickActions';
import { GoalTracker } from '../widgets/GoalTracker';
import { PerformanceWidget } from '../vault/PerformanceWidget';
import { HabitStatistics } from '../vault/HabitStatistics';
import { endpoints, type VaultSummary } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';

interface HabitStat {
  habit: string;
  records_this_month: number;
  days_missed: number;
  is_new_record: boolean;
}

export const Sidebar = () => {
  const { user } = useAuth();
  const [summary, setSummary] = useState<VaultSummary | null>(null);
  const [stats, setStats] = useState<HabitStat[]>([]);
  const [streakGraph, setStreakGraph] = useState<{ date: string; streak_length: number }[]>([]);

  useEffect(() => {
    endpoints.vault.summary().then(setSummary).catch(() => {});
    endpoints.habits.list().then((habits) => {
      if (habits[0]) {
        endpoints.habits.stats(habits[0].id)
          .then((s) => setStreakGraph(s.streak_graph))
          .catch(() => {});
      }
      Promise.all(
        habits.slice(0, 4).map((h) =>
          endpoints.habits.stats(h.id).then((s) => ({
            habit: h.name,
            records_this_month: s.records_this_month,
            days_missed: s.days_missed,
            is_new_record: s.is_new_record,
          })),
        ),
      ).then(setStats).catch(() => {});
    }).catch(() => {});
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">🎓 Student OS</div>
      {user && <div className="sidebar-user">{user.name} · {user.role ?? 'student'}</div>}
      <ThemeSwitcher />
      <NavLinks />
      <div className="sidebar-widgets">
        {summary && (
          <PerformanceWidget
            date={new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
            overdueTasks={summary.overdue_tasks}
            overdueLastWeek={summary.overdue_tasks}
            streakGraph={streakGraph}
          />
        )}
        {stats.length > 0 && <HabitStatistics stats={stats} />}
        <GoalTracker />
        <QuickActions />
        <ProgressBars />
        <DigitalClock />
      </div>
    </aside>
  );
};
