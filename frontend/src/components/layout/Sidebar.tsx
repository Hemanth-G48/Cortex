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
import { useProfile } from '../../hooks/useProfile';

interface HabitStat {
  habit: string;
  records_this_month: number;
  days_missed: number;
  is_new_record: boolean;
}

export const Sidebar = () => {
  // Single-owner app: the owner profile is always present — no login/logout.
  const { profile: user } = useProfile();
  const [summary, setSummary] = useState<VaultSummary | null>(null);
  const [stats, setStats] = useState<HabitStat[]>([]);
  const [streakGraph, setStreakGraph] = useState<{ date: string; streak_length: number }[]>([]);
  // Defect #97 fix: poll vault jobs + health audit so the sidebar bell
  // reflects running/failed reindex jobs and new health flags without reload.
  const [jobCount, setJobCount] = useState(0);
  const [healthScore, setHealthScore] = useState<number | null>(null);

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

    // Initial load of jobs + health.
    Promise.all([
      endpoints.kb.jobs.list().then((j) => j.items.filter((x) => x.status === 'queued' || x.status === 'running').length),
      endpoints.kb.health().then((h) => h.score).catch(() => null),
    ]).then(([jobs, health]) => {
      setJobCount(jobs);
      setHealthScore(health);
    }).catch(() => {});

    // Poll every 60s so the bell stays live.
    const t = window.setInterval(() => {
      Promise.all([
        endpoints.kb.jobs.list().then((j) => j.items.filter((x) => x.status === 'queued' || x.status === 'running').length).catch(() => 0),
        endpoints.kb.health().then((h) => h.score).catch(() => null),
      ]).then(([jobs, health]) => {
        setJobCount(jobs);
        setHealthScore(health);
      }).catch(() => {});
    }, 60_000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">🎓 Student OS</div>
      {user && (
        <div className="sidebar-user">
          <span>{user.name}</span>
        </div>
      )}
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
        {jobCount > 0 && (
          <div className="sidebar-widget" style={{ padding: '0.5rem 0.75rem', background: 'var(--warning-muted)', color: 'var(--warning)', borderRadius: 6, fontSize: '0.72rem', fontWeight: 600 }}
            title="Active vault jobs (reindex / scan / health audit)">
            ⚙️ {jobCount} vault job{jobCount !== 1 ? 's' : ''} running
          </div>
        )}
        {healthScore != null && healthScore < 45 && (
          <div className="sidebar-widget" style={{ padding: '0.5rem 0.75rem', background: 'var(--danger-muted)', color: 'var(--danger)', borderRadius: 6, fontSize: '0.72rem', fontWeight: 600 }}
            title="Vault health audit score below 45 — consider running a rescan">
            🩺 Vault health {Math.round(healthScore)}/100
          </div>
        )}
        <GoalTracker />
        <QuickActions />
        <ProgressBars />
        <DigitalClock />
      </div>
    </aside>
  );
};
