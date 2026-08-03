import { lastNDays, mapLogs, type LogEntry } from '../../utils/vaultDates';

interface HeatmapGridProps {
  /** Log entries for this habit. */
  logs: LogEntry[];
  /** CSS color applied to filled cells (e.g. var(--habit-blue)). */
  color: string;
  /** Optional label shown above the grid, e.g. "Last 30 days". */
  monthLabel?: string;
  /** Number of cells per row (default 7). */
  columns?: number;
  /** Use count-based gradient intensity instead of binary fill (default true). */
  gradient?: boolean;
}

const CELL_SIZE = 20;
const CELL_GAP = 3;

/** Map a log count to an intensity level 0..5 (0 = empty). */
function intensityLevel(count = 0): number {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count <= 4) return 3;
  if (count <= 7) return 4;
  return 5;
}

/**
 * 7x7 (or columns x rows) block heatmap for a single habit's past month.
 * Each cell is one day; filled when a log for that date has completed=true.
 */
export const HeatmapGrid = ({ logs, color, monthLabel, columns = 7, gradient = true }: HeatmapGridProps) => {
  const days = lastNDays(columns * 7);
  const byDate = mapLogs(logs);

  return (
    <div className="heatmap">
      {monthLabel && <div className="heatmap-label vault-muted">{monthLabel}</div>}
      <div
        className="heatmap-grid"
        style={{ gridTemplateColumns: `repeat(${columns}, ${CELL_SIZE}px)`, gap: `${CELL_GAP}px`, ['--heat-color' as string]: color }}
      >
        {days.map((date) => {
          const log = byDate.get(date);
          const active = Boolean(log && log.completed);
          const level = intensityLevel(log?.count ?? 0);
          return (
            <div
              key={date}
              className={active
                ? `heat-cell heat-cell-active heat-cell-${gradient ? level : Math.min(level, 1)}`
                : 'heat-cell heat-cell-empty'}
              data-date={date}
              data-count={log?.count ?? 0}
              title={date}
              style={{
                width: CELL_SIZE,
                height: CELL_SIZE,
                border: active ? '1px solid transparent' : `1px solid var(--vault-border)`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
