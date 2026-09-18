import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { StudyHeatmap } from '../components/analytics/StudyHeatmap';
import { TimeTrackerBars } from '../components/analytics/TimeTrackerBars';
import { GradeTrendChart } from '../components/grades/GradeTrendChart';
import { endpoints } from '../services/api';
import type { AnalyticsSummary, GPAResponse, Grade, HeatmapDay, WeeklyFocus } from '../services/api';
import { toIso } from '../utils/vaultDates';

const fmtMinutes = (m: number) => {
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem ? `${h}h ${rem}m` : `${h}h`;
};

export const Analytics = () => {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [weekly, setWeekly] = useState<WeeklyFocus[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapDay[]>([]);
  const [gpaData, setGpaData] = useState<GPAResponse | null>(null);
  const [grades, setGrades] = useState<Grade[]>([]);
  const [trendCourse, setTrendCourse] = useState<number | null>(null);
  // Defect #68: habit-log days + vault daily-note days for the same heatmap.
  const [habitDays, setHabitDays] = useState<Set<string>>(new Set());
  const [noteDays, setNoteDays] = useState<Set<string>>(new Set());
  // Defect #41 fix: per-section error state with retry.
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Defect #67: size the analytics range from the vault's own activity
      // window (GET /api/kb/stats → first indexed note) instead of the fixed
      // 8/52-week defaults, clamped to a sane chart width.
      const vaultStats = await endpoints.kb.stats().catch(() => null);
      const weeksForRange = (() => {
        const first = vaultStats?.oldest_document_date;
        if (!first) return { weekly: 8, heatmap: 52 };
        const days = Math.ceil(
          (Date.now() - new Date(`${first}T00:00:00`).getTime()) / 86_400_000,
        );
        const heatmapWeeks = Math.min(156, Math.max(8, Math.ceil(days / 7)));
        return { weekly: Math.min(26, heatmapWeeks), heatmap: heatmapWeeks };
      })();
      const heatmapStart = toIso(
        new Date(Date.now() - weeksForRange.heatmap * 7 * 86_400_000),
      );
      const [s, w, h, gpa, grs, habitLogs, todayNotes] = await Promise.all([
        endpoints.analytics.summary(),
        endpoints.analytics.weeklyFocus(weeksForRange.weekly).catch(() => null),
        endpoints.analytics.heatmap(weeksForRange.heatmap).catch(() => null),
        endpoints.grades.gpa().catch(() => null),
        endpoints.grades.list().catch(() => null),
        endpoints.habits.calendar('good', heatmapStart, toIso(new Date())).catch(() => []),
        endpoints.kb.dailyNotes.today().catch(() => null),
      ]);
      setHabitDays(
        new Set(
          habitLogs.flatMap((day) => (day.logs.length > 0 ? [day.date] : [])),
        ),
      );
      // The daily-notes feed is day-scoped today; mark that date when the day
      // has any captured note so the overlay is honest about its coverage.
      setNoteDays(
        new Set(
          todayNotes && todayNotes.documents.length > 0 ? [todayNotes.date] : [],
        ),
      );
      setSummary(s);
      setWeekly(w ?? []);
      setHeatmap(h ?? []);
      setGpaData(gpa);
      setGrades(grs ?? []);
      setTrendCourse((cur) => cur ?? gpa?.courses[0]?.course_id ?? null);
    } catch {
      setError('Could not load analytics — is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Defect #40 fix: CSV export of the analytics data.
  const exportCsv = () => {
    const lines: string[] = [];
    lines.push('section,key,value');
    if (summary) {
      lines.push(`summary,total_focus_minutes,${summary.total_focus_minutes}`);
      lines.push(`summary,weekly_focus_minutes,${summary.weekly_focus_minutes}`);
      lines.push(`summary,completion_rate,${summary.completion_rate}`);
      lines.push(`summary,gpa,${summary.gpa ?? ''}`);
      lines.push(`summary,total_xp,${summary.total_xp}`);
      lines.push(`summary,level,${summary.level}`);
      lines.push(`summary,current_streak,${summary.current_streak}`);
    }
    weekly.forEach((w) => lines.push(`weekly_focus,${w.label},${w.minutes}`));
    heatmap.forEach((d) => lines.push(`heatmap,${d.date},${d.minutes}`));
    if (gpaData?.gpa !== undefined && gpaData !== null) lines.push(`gpa,cumulative,${gpaData.gpa}`);
    grades.forEach((g) => lines.push(`grade,${g.title},${g.points_earned}/${g.points_possible}`));

    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `slos-analytics-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const trendGrades = trendCourse !== null ? grades.filter((g) => g.course_id === trendCourse) : [];

  const stats = summary
    ? [
        { label: 'Total Focus', value: fmtMinutes(summary.total_focus_minutes), icon: '⏱️' },
        { label: 'This Week', value: fmtMinutes(summary.weekly_focus_minutes), icon: '📅' },
        { label: 'Completion', value: `${summary.completion_rate}%`, icon: '✅' },
        { label: 'GPA', value: summary.gpa !== null ? summary.gpa.toFixed(2) : '—', icon: '🎓' },
        { label: 'XP', value: String(summary.total_xp), icon: '⚡' },
        { label: 'Level', value: `Lv.${summary.level}`, icon: '🏆' },
        { label: 'Streak', value: `${summary.current_streak}d`, icon: '🔥' },
      ]
    : [];

  return (
    <div className="fade-in">
      <Header title="Analytics" />

      {error && (
        <div className="card" style={{ marginBottom: '1.5rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={() => void refresh()}>Retry</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <button type="button" className="btn btn-ghost" onClick={exportCsv} disabled={loading || !summary}>
          📤 Export CSV
        </button>
      </div>

      {/* Stat cards */}
      <div className="stat-grid" style={{ marginBottom: '1.5rem' }}>
        {stats.map((s) => (
          <div key={s.label} className="stat-tile">
            <div className="label">{s.icon} {s.label}</div>
            <div className="value">{s.value}</div>
            {s.label === 'Completion' && summary && (
              <div className="sub">
                {summary.completed_assignments}/{summary.total_assignments} assignments done
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="dashboard-grid-2col" style={{ marginBottom: '1.5rem' }}>
        {/* Weekly focus bars */}
        <div className="card">
          <h2 className="widget-title" style={{ marginBottom: '0.75rem' }}>📊 Weekly Focus</h2>
          <TimeTrackerBars data={weekly} />
        </div>

        {/* Grade trend */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', gap: '0.5rem', flexWrap: 'wrap' }}>
            <h2 className="widget-title" style={{ margin: 0 }}>📈 Grade Trend</h2>
            {gpaData && gpaData.courses.length > 0 && (
              <select value={trendCourse ?? ''} onChange={(e) => setTrendCourse(Number(e.target.value))} style={{ width: 'auto', fontSize: '0.7rem', padding: '0.25rem 0.4rem' }}>
                {gpaData.courses.map((c) => (
                  <option key={c.course_id} value={c.course_id}>{c.title}</option>
                ))}
              </select>
            )}
          </div>
          <GradeTrendChart grades={trendGrades} height={110} />
        </div>
      </div>

      {/* 52-week heatmap */}
      <div className="card">
        <h2 className="widget-title" style={{ marginBottom: '0.75rem' }}>
          🔥 Focus Heatmap (last {Math.max(8, Math.round(heatmap.length / 7))} weeks)
        </h2>
        <StudyHeatmap days={heatmap} habitDays={habitDays} noteDays={noteDays} />
      </div>
    </div>
  );
};
