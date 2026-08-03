import type { DailyLogStats, LifePlannerSummary } from '../../services/api';

interface DailyLogWidgetProps {
  summary: LifePlannerSummary;
  stats: DailyLogStats;
  onLogIn: () => void;
  busy?: boolean;
}

function formatMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h === 0) return `${m}m focused`;
  return `${h}h ${m.toString().padStart(2, '0')}m focused`;
}

function weekNumber(d: Date): number {
  const oneJan = new Date(d.getFullYear(), 0, 1);
  const days = Math.floor((d.getTime() - oneJan.getTime()) / 86400000);
  return Math.ceil((days + oneJan.getDay() + 1) / 7);
}

/** Life Planner sidebar widget: date, week, focused time, streaks, progress bars. */
export const DailyLogWidget = ({ summary, stats, onLogIn, busy }: DailyLogWidgetProps) => {
  const today = new Date();
  const yearProgress = Math.round(((today.getMonth() * 30.4 + today.getDate()) / 365) * 100);
  const monthProgress = stats.days_in_month > 0 ? Math.round((today.getDate() / stats.days_in_month) * 100) : 0;
  const weekProgress = Math.round(((today.getDay() + 6) % 7 + 1) / 7 * 100);

  return (
    <div className="card daily-log-widget">
      <div className="lp-section-title">Daily Log</div>
      <div className="dl-row">
        <span className="dl-label">Today</span>
        <span className="dl-value">
          {today.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
        </span>
      </div>
      <div className="dl-row">
        <span className="dl-label">Week</span>
        <span className="dl-value">Week {weekNumber(today)}</span>
      </div>
      <div className="dl-focus">{formatMinutes(summary.daily_log_today.time_focused)}</div>
      <div className="dl-row">
        <span className="dl-label">Current streak</span>
        <span className="dl-value">⭐ {summary.current_streak} day{summary.current_streak === 1 ? '' : 's'}</span>
      </div>
      <div className="dl-row">
        <span className="dl-label">Longest streak</span>
        <span className="dl-value">🏆 {summary.longest_streak} day{summary.longest_streak === 1 ? '' : 's'}</span>
      </div>
      <div className="dl-progress progress-bars" style={{ margin: '0.75rem 0' }}>
        <div className="pb-row">
          <span className="pb-label">Year</span>
          <div className="xp-bar"><div className="xp-fill" style={{ width: `${yearProgress}%` }} /></div>
          <span className="pb-value">{yearProgress}%</span>
        </div>
        <div className="pb-row">
          <span className="pb-label">Month</span>
          <div className="xp-bar"><div className="xp-fill" style={{ width: `${monthProgress}%` }} /></div>
          <span className="pb-value">{monthProgress}%</span>
        </div>
        <div className="pb-row">
          <span className="pb-label">Week</span>
          <div className="xp-bar"><div className="xp-fill" style={{ width: `${weekProgress}%` }} /></div>
          <span className="pb-value">{weekProgress}%</span>
        </div>
      </div>
      <button className="btn btn-primary" style={{ width: '100%' }} onClick={onLogIn} disabled={busy}>
        {busy ? 'Logging…' : 'Log In Today'}
      </button>
    </div>
  );
};
