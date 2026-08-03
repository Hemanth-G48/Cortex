import { useState } from 'react';

const DOW = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

function inSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Compact month calendar with navigation arrows and today highlighted. */
export const MiniCalendar = () => {
  const [cursor, setCursor] = useState(() => new Date());
  const today = new Date();

  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrev = new Date(year, month, 0).getDate();

  const cells: { day: number; other: boolean }[] = [];
  for (let i = 0; i < startOffset; i++) {
    cells.push({ day: daysInPrev - startOffset + i + 1, other: true });
  }
  for (let d = 1; d <= daysInMonth; d++) cells.push({ day: d, other: false });
  while (cells.length % 7 !== 0) cells.push({ day: cells.length - startOffset - daysInMonth + 1, other: true });

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
          // Reconstruct the actual date for "today" comparison.
          const realDate = c.other
            ? (i < startOffset ? new Date(year, month - 1, c.day) : new Date(year, month + 1, c.day))
            : new Date(year, month, c.day);
          return (
            <div
              key={i}
              className={`mc-day${c.other ? ' other' : ''}${inSameDay(realDate, today) ? ' today' : ''}`}
            >
              {c.day}
            </div>
          );
        })}
      </div>
    </div>
  );
};
