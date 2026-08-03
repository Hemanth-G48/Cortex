import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type { Reminder } from '../../services/api';
import { formatTime, relativeDate } from '../../utils/formatters';

/** List of reminders with relative dates */
export const RemindersList = () => {
  const [reminders, setReminders] = useState<Reminder[]>([]);

  useEffect(() => {
    endpoints.reminders.list().then(setReminders).catch(() => {});
  }, []);

  if (!reminders.length) {
    return <div className="reminders-empty">No reminders yet</div>;
  }

  return (
    <div className="reminders-list">
      {reminders.map((r) => (
        <div key={r.id} className={`reminder-row${r.is_completed ? ' done' : ''}`}>
          <div className="reminder-icon">{r.is_completed ? '✅' : '⏰'}</div>
          <div className="reminder-body">
            <div className="reminder-title">{r.title}</div>
            <div className="reminder-meta">
              {r.date && <span>{relativeDate(r.date)}</span>}
              {r.time && <span>at {formatTime(r.time)}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
