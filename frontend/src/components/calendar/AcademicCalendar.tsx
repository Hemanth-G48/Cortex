import { useMemo } from 'react';
import type { Task } from '../../services/api';

interface AcademicCalendarProps {
  tasks: Task[];
}

/** 7‑day academic calendar with task chips */
export const AcademicCalendar = ({ tasks }: AcademicCalendarProps) => {
  const weekDays = useMemo(() => {
    const days: { date: Date; label: string; active: boolean; tasks: Task[] }[] = [];
    const now = new Date();
    // Start from Monday of current week
    const mon = new Date(now);
    mon.setDate(now.getDate() - ((now.getDay() + 6) % 7));

    for (let i = 0; i < 7; i++) {
      const d = new Date(mon);
      d.setDate(mon.getDate() + i);
      const dateStr = d.toISOString().split('T')[0];
      const dayTasks = tasks.filter((t) => t.due_date === dateStr);
      const isToday = d.toDateString() === now.toDateString();
      days.push({
        date: d,
        label: d.toLocaleDateString('en', { weekday: 'short', day: 'numeric' }),
        active: isToday,
        tasks: dayTasks,
      });
    }
    return days;
  }, [tasks]);

  return (
    <div className="academic-calendar">
      <div className="calendar-header">
        <h2>This Week</h2>
      </div>
      <div className="calendar-week">
        {weekDays.map((d) => (
          <div key={d.date.toISOString()} className={`calendar-day${d.active ? ' today' : ''}`}>
            <div className="calendar-day-label">{d.label}</div>
            <div className="calendar-day-tasks">
              {d.tasks.length > 0 ? (
                d.tasks.slice(0, 3).map((t) => (
                  <div
                    key={t.id}
                    className="calendar-task-chip"
                    style={{
                      background: t.status === 'Completed' ? 'rgba(78,205,196,0.15)' : 'var(--accent-muted)',
                      borderLeft: `2px solid ${t.status === 'Completed' ? 'var(--success)' : 'var(--accent)'}`,
                    }}
                  >
                    <span style={{ textDecoration: t.status === 'Completed' ? 'line-through' : 'none' }}>{t.title}</span>
                  </div>
                ))
              ) : (
                <div className="calendar-empty" />
              )}
              {d.tasks.length > 3 && (
                <div className="calendar-more">+{d.tasks.length - 3} more</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
