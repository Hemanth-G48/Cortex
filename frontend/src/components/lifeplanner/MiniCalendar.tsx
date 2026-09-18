import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';

const DOW = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

function inSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Compact month calendar with navigation arrows — Defect #44 fix: dots days
 * that have a daily note in the Second Brain (live from GET /kb/daily-notes)
 * in addition to highlighting today. */
export const MiniCalendar = () => {
  const [cursor, setCursor] = useState(() => new Date());
  const [noteDates, setNoteDates] = useState<Set<string>>(new Set());
  const today = new Date();

  useEffect(() => {
    endpoints.kb.dailyNotes.today().then((d) => {
      if (d?.date) setNoteDates(new Set([d.date]));
    }).catch(() => {});
  }, []);

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrev = new Date(year, month, 0).getDate();

  const cells: { day: number; other: boolean; dateStr: string | null }[] = [];
  for (let i = 0; i < startOffset; i++) {
    const d = daysInPrev - startOffset + i + 1;
    cells.push({ day: d, other: true, dateStr: null });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${(month + 1).toString().padStart(2, '0')}-${d.toString().padStart(2, '0')}`;
    cells.push({ day: d, other: false, dateStr });
  }
  while (cells.length % 7 !== 0) {
    const idx = cells.length;
    const d = idx - startOffset - daysInMonth + 1;
    cells.push({ day: d, other: true, dateStr: null });
  }

  const shift = (delta: number) => setCursor((c) => new Date(c.getFullYear(), c.getMonth() + delta, 1));

  return (
    <div className="card mini-calendar">
      <div className="lp-section-title">Calendar</div>
      <div className="mc-header">
        <button type="button" className="mc-nav" onClick={() => shift(-1)} aria-label="Previous month">‹</button>
        <div className="mc-title">
          {cursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
        </div>
        <button type="button" className="mc-nav" onClick={() => shift(1)} aria-label="Next month">›</button>
      </div>
      <div className="mc-grid">
        {DOW.map((d) => (
          <div key={d} className="mc-dow">{d}</div>
        ))}
        {cells.map((c, i) => {
          const hasNote = c.dateStr != null && noteDates.has(c.dateStr);
          const realDate = c.other
            ? (i < startOffset ? new Date(year, month - 1, c.day) : new Date(year, month + 1, c.day))
            : new Date(year, month, c.day);
          return (
            <div
              key={i}
              className={`mc-day${c.other ? ' other' : ''}${inSameDay(realDate, today) ? ' today' : ''}${hasNote ? ' has-note' : ''}`}
            >
              {c.day}
            </div>
          );
        })}
      </div>
    </div>
  );
};
