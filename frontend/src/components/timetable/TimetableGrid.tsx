import type { ScheduleEvent } from '../../services/api';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'] as const;
const HOURS = ['8:00', '9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00'];

function timeToSlot(time: string | null): string {
  if (!time) return '8:00';
  const h = parseInt(time.split(':')[0], 10);
  return `${h}:00`;
}

interface TimetableGridProps {
  entries: ScheduleEvent[];
}

/** CSS grid timetable (80px × 5 columns) */
export const TimetableGrid = ({ entries }: TimetableGridProps) => {
  return (
    <div className="timetable-wrapper">
      <div className="timetable-header">
        <div className="timetable-corner" />
        {DAYS.map((d) => <div key={d} className="timetable-day-label">{d}</div>)}
      </div>
      <div className="timetable-body">
        <div className="timetable-times">
          {HOURS.map((t) => (
            <div key={t} className="timetable-time-label">{t}</div>
          ))}
        </div>
        <div className="timetable-grid">
          {DAYS.map((day) => (
            <div key={day} className="timetable-col">
              {HOURS.map((slot) => {
                const dayIndex = DAYS.indexOf(day);
                const entry = entries.find(
                  (e) => e.day_of_week === dayIndex && timeToSlot(e.start_time) === slot
                );
                return (
                  <div key={slot} className="timetable-cell">
                    {entry && (
                      <div
                        className="timetable-entry"
                        style={{ background: entry.color ? `${entry.color}25` : 'var(--accent-muted)', borderLeft: `3px solid ${entry.color ?? 'var(--accent)'}` }}
                      >
                        <span className="tt-entry-name">{entry.title}</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
