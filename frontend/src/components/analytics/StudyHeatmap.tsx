import type { HeatmapDay } from '../../services/api';

interface StudyHeatmapProps {
  days: HeatmapDay[];
  /** ISO dates with a habit log (GET /habit-logs/calendar) — defect #68. */
  habitDays?: Set<string>;
  /** ISO dates with a vault daily note (GET /api/kb/daily-notes) — defect #68. */
  noteDays?: Set<string>;
}

const intensityColor = (minutes: number) => {
  if (minutes <= 0) return 'var(--bg-hover)';
  if (minutes < 25) return 'rgba(78, 205, 196, 0.28)';
  if (minutes < 50) return 'rgba(78, 205, 196, 0.5)';
  if (minutes < 100) return 'rgba(78, 205, 196, 0.75)';
  return 'var(--success)';
};

/**
 * 52-week focus heatmap (port of Shiori's StudyHeatmap). Renders one column
 * per week, 7 cells tall, colored by daily focus minutes.
 */
export const StudyHeatmap = ({ days, habitDays, noteDays }: StudyHeatmapProps) => {
  if (days.length === 0) {
    return <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '1rem 0' }}>No focus data yet.</div>;
  }

  // Group by ISO week (Monday-start) for column rendering.
  const weeks = new Map<string, HeatmapDay[]>();
  for (const d of days) {
    const date = new Date(d.date);
    const monday = new Date(date);
    const dow = (date.getDay() + 6) % 7; // Monday=0
    monday.setDate(date.getDate() - dow);
    const key = monday.toISOString().slice(0, 10);
    if (!weeks.has(key)) weeks.set(key, []);
    weeks.get(key)!.push(d);
  }

  const columns = Array.from(weeks.values());

  const totalMinutes = days.reduce((s, d) => s + d.minutes, 0);
  const activeDays = days.filter((d) => d.minutes > 0).length;

  return (
    <div>
      <div style={{ display: 'flex', gap: '2px', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {columns.map((week, wi) => (
          <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {week.map((d) => {
              // Defect #68: same colour scale, but the cell also marks the
              // vault's habit logs and daily notes for that day.
              const hasHabit = habitDays?.has(d.date) ?? false;
              const hasNote = noteDays?.has(d.date) ?? false;
              const marks = [hasHabit ? 'habit logged' : null, hasNote ? 'daily note' : null]
                .filter(Boolean)
                .join(' · ');
              return (
                <div
                  key={d.date}
                  title={`${d.date}: ${d.minutes} min${marks ? ` (${marks})` : ''}`}
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: 2,
                    background: intensityColor(d.minutes),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 8,
                    lineHeight: 1,
                    color: hasHabit || hasNote ? 'var(--text-primary)' : 'transparent',
                  }}
                >
                  {hasNote ? '•' : hasHabit ? '·' : ''}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
        <span>
          {activeDays} active days · {totalMinutes} min total
          {habitDays && habitDays.size > 0 ? ` · ${habitDays.size} habit-log days` : ''}
          {noteDays && noteDays.size > 0 ? ` · ${noteDays.size} daily notes` : ''}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
          Less
          {[0, 25, 50, 100, 150].map((m) => (
            <span key={m} style={{ width: 10, height: 10, borderRadius: 2, background: intensityColor(m), display: 'inline-block' }} />
          ))}
          More
        </span>
      </div>
    </div>
  );
};
