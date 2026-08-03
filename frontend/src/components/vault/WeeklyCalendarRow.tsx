import type { CalendarTask } from '../../services/api';

interface CalendarDayCol {
  date: string;
  label?: string;
  tasks: CalendarTask[];
}

interface WeeklyCalendarRowProps {
  /** Seven day columns (Mon..Sun) with tasks plotted per date. */
  days: CalendarDayCol[];
  onComplete: (taskId: number) => void;
  onOpen: (dayOfWeek: number) => void;
}

/** 7-day calendar strip: day columns with task chips + per-task actions. */
export const WeeklyCalendarRow = ({ days, onComplete, onOpen }: WeeklyCalendarRowProps) => (
  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(days.length, 1)}, 1fr)`, gap: 10 }}>
    {days.map((day) => {
      const todayIso = new Date().toISOString().split('T')[0];
      const isToday = day.date === todayIso;
      return (
        <div
          key={day.date}
          style={{
            background: 'var(--vault-bg-card)',
            border: `1px solid ${isToday ? 'var(--habit-blue)' : 'var(--vault-border)'}`,
            borderRadius: 8,
            padding: 10,
            minHeight: 120,
          }}
        >
          <div
            className="vault-muted"
            style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: isToday ? 'var(--habit-blue)' : undefined }}
          >
            {day.label ?? day.date}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {day.tasks.map((task) => {
              const done = task.status === 'Completed';
              return (
                <div
                  key={task.id}
                  style={{
                    border: '1px solid var(--vault-border)',
                    borderRadius: 6,
                    padding: '4px 6px',
                    fontSize: 12,
                    background: 'var(--vault-bg-main)',
                    textDecoration: done ? 'line-through' : 'none',
                    color: done ? 'var(--vault-text-muted)' : 'var(--vault-text-primary)',
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{task.title}</div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <button
                      onClick={() => onComplete(task.id)}
                      disabled={done}
                      style={{
                        background: 'none', border: 'none', cursor: done ? 'default' : 'pointer',
                        color: done ? 'var(--success-teal)' : 'var(--habit-blue)', fontSize: 11, padding: 0, fontWeight: 600,
                      }}
                    >
                      Mark as comp.
                    </button>
                    <button
                      onClick={() => onOpen(days.indexOf(day))}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--vault-text-muted)', fontSize: 11, padding: 0 }}
                    >
                      Open in Calendar
                    </button>
                  </div>
                </div>
              );
            })}
            {day.tasks.length === 0 && <div className="vault-muted" style={{ fontSize: 11 }}>—</div>}
          </div>
        </div>
      );
    })}
  </div>
);
