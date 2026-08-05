import type { WeeklyFocus } from '../../services/api';

interface TimeTrackerBarsProps {
  data: WeeklyFocus[];
}

/**
 * Vertical bar chart of weekly focus minutes (port of Shiori's
 * TimeTrackerBars). Pure presentational; bars are pure CSS.
 */
export const TimeTrackerBars = ({ data }: TimeTrackerBarsProps) => {
  if (data.length === 0) {
    return <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', padding: '1rem 0' }}>No focus data yet.</div>;
  }

  const max = Math.max(...data.map((d) => d.minutes), 1);
  const total = data.reduce((s, d) => s + d.minutes, 0);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', height: 140, padding: '0.25rem 0' }}>
        {data.map((d, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem', height: '100%', justifyContent: 'flex-end' }}>
            <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>{d.minutes > 0 ? `${d.minutes}m` : ''}</span>
            <div
              title={`${d.label}: ${d.minutes} min`}
              style={{
                width: '100%',
                height: `${Math.max((d.minutes / max) * 100, 2)}%`,
                background: 'linear-gradient(180deg, var(--info), var(--accent))',
                borderRadius: '4px 4px 0 0',
                minHeight: 3,
                opacity: d.minutes > 0 ? 1 : 0.25,
                transition: 'height 0.3s ease',
              }}
            />
            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
              {new Date(d.label + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
        {total} minutes of focused work across {data.filter((d) => d.minutes > 0).length} active weeks
      </div>
    </div>
  );
};
