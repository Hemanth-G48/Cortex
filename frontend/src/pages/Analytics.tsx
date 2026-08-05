import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { StudyHeatmap } from '../components/analytics/StudyHeatmap';
import { TimeTrackerBars } from '../components/analytics/TimeTrackerBars';
import { GradeTrendChart } from '../components/grades/GradeTrendChart';
import { endpoints } from '../services/api';
import type { AnalyticsSummary, GPAResponse, Grade, HeatmapDay, WeeklyFocus } from '../services/api';

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

  const refresh = useCallback(async () => {
    try {
      const [s, w, h, gpa, grs] = await Promise.all([
        endpoints.analytics.summary(),
        endpoints.analytics.weeklyFocus(),
        endpoints.analytics.heatmap(),
        endpoints.grades.gpa().catch(() => null),
        endpoints.grades.list().catch(() => []),
      ]);
      setSummary(s);
      setWeekly(w);
      setHeatmap(h);
      setGpaData(gpa);
      setGrades(grs);
      setTrendCourse((cur) => cur ?? gpa?.courses[0]?.course_id ?? null);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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
        <h2 className="widget-title" style={{ marginBottom: '0.75rem' }}>🔥 Focus Heatmap (last 52 weeks)</h2>
        <StudyHeatmap days={heatmap} />
      </div>
    </div>
  );
};
