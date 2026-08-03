import { useId } from 'react';

interface StreakPoint {
  date: string;
  streak_length: number;
}

interface PerformanceWidgetProps {
  /** Current date label, e.g. "Tue, Jul 31". */
  date: string;
  /** Overdue tasks count for the badge. */
  overdueTasks: number;
  /** "You have N tasks overdue last week". */
  overdueLastWeek: number;
  /** Last month's streak graph for the mini line chart (UX #5). */
  streakGraph?: StreakPoint[];
}

/** Small inline SVG line chart of streak lengths over the past 30 days. */
const StreakLineGraph = ({ data }: { data: StreakPoint[] }) => {
  const gradId = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  if (!data || data.length < 2) return null;

  const W = 220;
  const H = 48;
  const pad = 4;
  const max = Math.max(1, ...data.map((d) => d.streak_length));
  const step = (W - pad * 2) / (data.length - 1);

  const points = data.map((d, i) => {
    const x = pad + i * step;
    const y = H - pad - (d.streak_length / max) * (H - pad * 2);
    return `${x},${y}`;
  });

  const path = `M${points.join(' L')}`;
  const area = `${path} L${W - pad},${H - pad} L${pad},${H - pad} Z`;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Last month streak trend"
      style={{ display: 'block', marginTop: 10 }}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--habit-blue)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--habit-blue)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradId})`} />
      <path
        d={path}
        fill="none"
        stroke="var(--habit-blue)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
};

/** Vault top widget: current date, motivational greeting, overdue counts, streak mini-chart. */
export const PerformanceWidget = ({ date, overdueTasks, overdueLastWeek, streakGraph }: PerformanceWidgetProps) => (
  <div className="vault-card">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
      <div>
        <div className="vault-muted">{date}</div>
        <div className="vault-body" style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
          Good day! Organized dashboard…
        </div>
      </div>
      <div style={{ display: 'flex', gap: 10 }}>
        <span
          style={{
            background: 'var(--habit-red)',
            color: '#fff',
            borderRadius: 6,
            padding: '6px 10px',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Overdue Tasks: {overdueTasks}
        </span>
      </div>
    </div>
    <div className="vault-muted" style={{ marginTop: 10 }}>
      You have {overdueLastWeek} tasks overdue last week
    </div>
    <StreakLineGraph data={streakGraph ?? []} />
  </div>
);
