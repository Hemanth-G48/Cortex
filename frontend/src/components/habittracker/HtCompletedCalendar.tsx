import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { endpoints } from '../../services/api';
import { toIso } from '../../utils/vaultDates';
import type { HabitCalendarDay, HabitCalendarLog } from '../../services/api';

interface Props {
  type: 'good' | 'bad';
  /** Bump to refetch (e.g. after a complete/admit action elsewhere on the page). */
  refreshKey?: number;
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

type ViewMode = 'week' | 'month';

const iso = (d: Date) => toIso(d);

/** Monday-based week start. */
const weekStartOf = (base: Date): Date => {
  const d = new Date(base);
  d.setHours(0, 0, 0, 0);
  const diff = d.getDay() === 0 ? -6 : 1 - d.getDay();
  d.setDate(d.getDate() + diff);
  return d;
};

/**
 * Completed-Good / Completed-Bad weekly calendar rows (Phases 85-91):
 * 7 day columns with habit logs plotted on dates, color-coded dots,
 * week/month toggle, uncompleted filter, HTML5 drag-and-drop reorder within
 * a day (persisted via sort_order), and an Open-in-Calendar link.
 */
export const HtCompletedCalendar = ({ type, refreshKey = 0 }: Props) => {
  const [viewMode, setViewMode] = useState<ViewMode>('week');
  const [weekOffset, setWeekOffset] = useState(0);
  const [monthOffset, setMonthOffset] = useState(0);
  const [days, setDays] = useState<HabitCalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [onlyUncompleted, setOnlyUncompleted] = useState(false);
  // Phase 91 drag state: the log being dragged + the insertion slot.
  const [dragId, setDragId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState<{ day: string; index: number } | null>(null);

  const good = type === 'good';

  const weekStart = useMemo(() => {
    const base = new Date();
    base.setDate(base.getDate() + weekOffset * 7);
    return weekStartOf(base);
  }, [weekOffset]);

  const monthStart = useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth() + monthOffset, 1);
  }, [monthOffset]);

  const computeRange = useCallback((): { start: Date; end: Date } => {
    if (viewMode === 'week') {
      const end = new Date(weekStart);
      end.setDate(weekStart.getDate() + 6);
      return { start: weekStart, end };
    }
    const end = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0);
    return { start: monthStart, end };
  }, [viewMode, weekStart, monthStart]);

  const fetchRange = useCallback(async (start: Date, end: Date) => {
    setLoading(true);
    try {
      const data = await endpoints.habits.calendar(type, iso(start), iso(end));
      setDays(data);
    } catch {
      setDays([]);
    } finally {
      setLoading(false);
    }
  }, [type]);

  useEffect(() => {
    const { start, end } = computeRange();
    void fetchRange(start, end);
  }, [computeRange, fetchRange, refreshKey]);

  const byDate = useMemo(() => {
    const m = new Map<string, HabitCalendarDay>();
    for (const day of days) m.set(day.date, day);
    return m;
  }, [days]);

  const weekDates = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(weekStart);
      d.setDate(weekStart.getDate() + i);
      return d;
    });
  }, [weekStart]);

  const monthCells = useMemo(() => {
    const firstDow = (monthStart.getDay() + 6) % 7; // Monday-first
    const total = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
    const cells: (Date | null)[] = [];
    for (let i = 0; i < firstDow; i++) cells.push(null);
    for (let d = 1; d <= total; d++) cells.push(new Date(monthStart.getFullYear(), monthStart.getMonth(), d));
    return cells;
  }, [monthStart]);

  const filteredLogs = useCallback(
    (day: string) => {
      const logs = byDate.get(day)?.logs ?? [];
      return onlyUncompleted ? logs.filter((l) => !l.completed) : logs;
    },
    [byDate, onlyUncompleted],
  );

  // ── Phase 91: drag-and-drop within a day column ──
  const handleDragStart = useCallback((e: React.DragEvent, log: HabitCalendarLog) => {
    setDragId(log.id);
    e.dataTransfer.setData('text/plain', String(log.id));
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, day: string, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOver({ day, index });
  }, []);

  const clearDrag = useCallback(() => {
    setDragId(null);
    setDragOver(null);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent, day: string) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData('text/plain');
      const draggedId = Number(raw);
      const target = dragOver?.day === day ? dragOver.index : null;
      clearDrag();
      if (!Number.isFinite(draggedId) || target === null) return;

      const logs = filteredLogs(day);
      const from = logs.findIndex((l) => l.id === draggedId);
      if (from === -1 || from === target) return;
      const reordered = [...logs];
      const [moved] = reordered.splice(from, 1);
      // The marker sits BEFORE the hovered item (index `target`). Removing an
      // earlier item shifts everything left, so a downward drag inserts one
      // slot earlier to land exactly where the marker showed. (Phase 91)
      const insertAt = from < target ? target - 1 : target;
      reordered.splice(insertAt, 0, moved);
      try {
        await endpoints.habits.reorder(reordered.map((l) => l.id));
        const { start, end } = computeRange();
        await fetchRange(start, end);
      } catch {
        /* drag persistence is best-effort */
      }
    },
    [dragOver, clearDrag, filteredLogs, computeRange, fetchRange],
  );

  // Clear the insertion marker once the pointer leaves the whole day column.
  const handleColumnDragLeave = useCallback((e: React.DragEvent) => {
    const related = e.relatedTarget as Node | null;
    if (!related || !e.currentTarget.contains(related)) {
      clearDrag();
    }
  }, [clearDrag]);

  const renderItem = (l: HabitCalendarLog, day: string, index: number, compact = false) => {
    const isDragTarget = dragOver?.day === day && dragOver.index === index;
    // Phase 91 drag only applies to the full week-view list (no filter, not compact).
    const draggable = !compact && !onlyUncompleted;
    return (
      <div key={l.id} style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
        {isDragTarget && !compact && <div className="ht-drag-marker" aria-hidden="true" />}
        <div
          className={`ht-cal-item${dragId === l.id ? ' ht-dragging' : ''}`}
          draggable={draggable}
          onDragStart={draggable ? (e) => handleDragStart(e, l) : undefined}
          onDragOver={draggable ? (e) => handleDragOver(e, day, index) : undefined}
          onDragEnd={clearDrag}
          onDrop={draggable ? (e) => void handleDrop(e, day) : undefined}
          style={compact ? { display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.2rem 0.35rem' } : undefined}
        >
          {!compact && (
            <span className="ht-drag-handle" aria-hidden="true" title="Drag to reorder">⠿</span>
          )}
          <span className={`ht-dot ${good ? 'ht-dot-good' : 'ht-dot-bad'}`} aria-hidden="true" />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.habit_name}</span>
          {!compact && (
            <span className={`ht-cal-xp ${l.xp_change >= 0 ? 'plus' : 'minus'}`}>
              {l.xp_change >= 0 ? '+' : ''}{l.xp_change}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderDayColumn = (d: Date) => {
    const key = iso(d);
    const logs = filteredLogs(key);
    const today = iso(new Date()) === key;
    return (
      <div
        key={key}
        className="ht-card"
        style={{ padding: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}
        onDragLeave={handleColumnDragLeave}
        onDrop={(e) => { e.preventDefault(); clearDrag(); }}
      >
        <div className={`ht-cal-day-head${today ? ' today' : ''}`}>
          {DAY_NAMES[(d.getDay() + 6) % 7]} {d.getDate()}
        </div>
        {logs.length === 0 ? (
          <div className="ht-cal-empty">—</div>
        ) : (
          logs.map((l, i) => renderItem(l, key, i))
        )}
      </div>
    );
  };

  const renderMonthGrid = () => (
    <div className="ht-cal-scroll">
      <div className="ht-calendar-row" style={{ minWidth: '600px' }}>
        {DAY_NAMES.map((d) => (
          <div key={d} className="ht-cal-day-head" style={{ borderBottom: 'none', marginBottom: 0 }}>{d}</div>
        ))}
        {monthCells.map((d, i) => {
          if (!d) return <div key={`e${i}`} />;
          const key = iso(d);
          const logs = filteredLogs(key);
          const today = iso(new Date()) === key;
          return (
            <div key={key} className="ht-card" style={{ padding: '0.4rem', minHeight: 64, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div className={`ht-cal-day-head${today ? ' today' : ''}`} style={{ borderBottom: 'none', marginBottom: 0, textAlign: 'right' }}>{d.getDate()}</div>
              {logs.slice(0, 3).map((l) => renderItem(l, key, i, true))}
              {logs.length > 3 && <div className="ht-cal-empty">+{logs.length - 3} more</div>}
            </div>
          );
        })}
      </div>
    </div>
  );

  const weekRangeLabel = `${weekDates[0].getDate()} ${MONTH_NAMES[weekDates[0].getMonth()]} — ${weekDates[6].getDate()} ${MONTH_NAMES[weekDates[6].getMonth()]}`;

  return (
    <div className="ht-row">
      <div className="ht-row-header">
        <div className="ht-row-title">
          <span className="ht-row-emoji">{good ? '✅' : '📉'}</span>
          Completed {good ? 'Good' : 'Bad'} Habits
        </div>
        <div className="ht-calendar-controls">
          <div className="ht-cal-view-toggle">
            <button type="button" className={`ht-cal-view-btn${viewMode === 'week' ? ' active' : ''}`} onClick={() => setViewMode('week')}>Week</button>
            <button type="button" className={`ht-cal-view-btn${viewMode === 'month' ? ' active' : ''}`} onClick={() => setViewMode('month')}>Month</button>
          </div>
          {viewMode === 'week' ? (
            <>
              <button type="button" className="ht-cal-nav-btn" onClick={() => setWeekOffset((o) => o - 1)} aria-label="Previous week">◀</button>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{weekRangeLabel}</span>
              <button type="button" className="ht-cal-nav-btn" onClick={() => setWeekOffset((o) => o + 1)} aria-label="Next week">▶</button>
            </>
          ) : (
            <>
              <button type="button" className="ht-cal-nav-btn" onClick={() => setMonthOffset((o) => o - 1)} aria-label="Previous month">◀</button>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                {MONTH_NAMES[monthStart.getMonth()]} {monthStart.getFullYear()}
              </span>
              <button type="button" className="ht-cal-nav-btn" onClick={() => setMonthOffset((o) => o + 1)} aria-label="Next month">▶</button>
            </>
          )}
          <label className="ht-uncompleted-filter">
            <input type="checkbox" checked={onlyUncompleted} onChange={(e) => setOnlyUncompleted(e.target.checked)} />
            Show only uncompleted
          </label>
          <Link to="/schedule" className="ht-cal-open-link">Open in Calendar ↗</Link>
        </div>
      </div>

      {loading ? (
        <div className="ht-card ht-cal-empty">⏳ Loading {good ? 'good' : 'bad'} habit calendar…</div>
      ) : viewMode === 'week' ? (
        <div className="ht-cal-scroll">
          <div className="ht-calendar-row">{weekDates.map(renderDayColumn)}</div>
        </div>
      ) : (
        renderMonthGrid()
      )}
    </div>
  );
};
