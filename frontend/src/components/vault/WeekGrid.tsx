import { lastNDays, mapLogs, toIso, type LogEntry } from '../../utils/vaultDates';

interface WeekGridProps {
  /** Log entries for this habit. */
  logs: LogEntry[];
  /** CSS color for completed cells (e.g. var(--habit-blue)). */
  color: string;
  /** Number of weeks to show (default 4). */
  weeks?: number;
}

const CELL = 14;
const GAP = 2;

/**
 * Compact 4-week x 7-day checkmark grid for streak cards.
 * ✓ = completed log for that date, ✗ = date passed with no completed log, · = future.
 */
export const WeekGrid = ({ logs, color, weeks = 4 }: WeekGridProps) => {
  const size = weeks * 7;
  const days = lastNDays(size);
  const byDate = mapLogs(logs);

  // Today ISO (only first `size` days are in the past range; the last cell is today).
  const todayIso = toIso(new Date());
  const todayIndex = days.indexOf(todayIso);

  return (
    <div
      className="weekgrid"
      style={{ gridTemplateColumns: `repeat(${weeks}, ${CELL}px)`, gridAutoFlow: 'column', gap: `${GAP}px` }}
    >
      {days.map((date, i) => {
        const log = byDate.get(date);
        const isPast = i < todayIndex || (i === todayIndex && log);
        let state: 'done' | 'missed' | 'blank' = 'blank';
        if (log && log.completed) state = 'done';
        else if (isPast) state = 'missed';

        return (
          <div
            key={date}
            className={`week-cell week-cell-${state}`}
            data-date={date}
            title={date}
            style={{
              width: CELL,
              height: CELL,
              fontSize: CELL - 6,
              lineHeight: `${CELL}px`,
              background: state === 'done' ? color : 'transparent',
              border: state === 'done' ? '1px solid transparent' : '1px solid var(--vault-border)',
              color: state === 'done' ? '#fff' : 'var(--vault-text-muted)',
            }}
          >
            {state === 'done' ? '✓' : state === 'missed' ? '✗' : '·'}
          </div>
        );
      })}
    </div>
  );
};
