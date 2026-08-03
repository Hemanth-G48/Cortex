import type { Task } from '../../services/api';

interface WeekProgressStripProps {
  /** All tasks (completed + pending) to aggregate by due date this week. */
  tasks: Task[];
}

/** Compact 7-day progress strip: completed-vs-total tasks per day (Mon..Sun). */
export const WeekProgressStrip = ({ tasks }: WeekProgressStripProps) => {
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - now.getDay() + (now.getDay() === 0 ? -6 : 1));

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8, marginBottom: 12 }}>
      {days.map((d) => {
        const iso = d.toISOString().split('T')[0];
        const dayTasks = tasks.filter((t) => t.due_date === iso);
        const done = dayTasks.filter((t) => t.status === 'Completed').length;
        const total = dayTasks.length;
        const pct = total === 0 ? 0 : Math.round((done / total) * 100);
        return (
          <div key={iso} style={{ textAlign: 'center' }}>
            <div className="vault-muted" style={{ fontSize: 11, fontWeight: 700 }}>
              {d.toLocaleDateString(undefined, { weekday: 'short' })}
            </div>
            <div
              style={{
                height: 5,
                borderRadius: 3,
                background: 'var(--vault-border)',
                overflow: 'hidden',
                margin: '4px 0 2px',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: pct === 100 && total > 0 ? 'var(--success-teal)' : 'var(--habit-blue)',
                }}
              />
            </div>
            <div className="vault-muted" style={{ fontSize: 11 }}>
              {done}/{total}
            </div>
          </div>
        );
      })}
    </div>
  );
};
