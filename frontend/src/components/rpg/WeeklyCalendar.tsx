import { useState, useEffect, useMemo, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { format, isToday, startOfMonth, endOfMonth, eachDayOfInterval, getDay, addMonths } from 'date-fns';
import { RpgCard } from './RpgCard';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Quest, Mission, QuestDateGroup, QuestCentreCalendar, CalendarQuest } from '../../services/api';

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function getWeekRange(date: Date): { start: Date; end: Date } {
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const start = new Date(date);
  start.setDate(date.getDate() + diff);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { start, end };
}

function formatDate(date: Date): string {
  return `${date.getDate()}/${date.getMonth() + 1}`;
}

function getDayDates(start: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

function dateToDayOfWeek(date: Date): number {
  const jsDay = date.getDay();
  return jsDay === 0 ? 6 : jsDay - 1;
}

interface CalendarEvent {
  id: number | string;
  title: string;
  day_of_week: number;
  start_time: string | null;
  end_time?: string | null;
  reference_type: string | null;
  color: string | null;
  type: 'schedule' | 'quest' | 'mission';
  source_id?: number;
  due_date?: string;
}

type ViewMode = 'week' | 'month';

interface WeeklyCalendarProps {
  questsByDate?: QuestDateGroup[];
  view?: ViewMode;
}

const typeColors: Record<string, string> = {
  quest: '#ff9800',
  mission: '#4caf50',
  task: '#2196f3',
  schedule: '#9c27b0',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  backgroundColor: '#2a2a2a',
  border: '1px solid #3a3a3a',
  padding: '4px 6px',
  borderRadius: 4,
  color: '#fff',
  fontSize: 11,
  boxSizing: 'border-box',
  outline: 'none',
  marginBottom: 4,
};

export const WeeklyCalendar = ({
  questsByDate: questsByDateProp,
  view: viewProp,
}: WeeklyCalendarProps = {}) => {
  const navigate = useNavigate();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [weekStart, setWeekStart] = useState(() => getWeekRange(new Date()).start);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>(viewProp ?? 'week');
  const [creatingDayIndex, setCreatingDayIndex] = useState<number | null>(null);
  const [quickTitle, setQuickTitle] = useState('');
  const [quickStart, setQuickStart] = useState('');
  const [quickEnd, setQuickEnd] = useState('');
  const [dragId, setDragId] = useState<string | null>(null);
  const [monthOffset, setMonthOffset] = useState(0);
  const [expandedDay, setExpandedDay] = useState<number | null>(null);

  const monthStart = useMemo(() => {
    const now = new Date();
    return startOfMonth(addMonths(now, monthOffset));
  }, [monthOffset]);

  const monthDays = useMemo(() => {
    const start = startOfMonth(monthStart);
    const end = endOfMonth(monthStart);
    const days = eachDayOfInterval({ start, end });
    const firstDayOfWeek = getDay(start) === 0 ? 6 : getDay(start) - 1;
    const padded: (Date | null)[] = [];
    for (let i = 0; i < firstDayOfWeek; i++) {
      padded.push(null);
    }
    return [...padded, ...days];
  }, [monthStart]);

  // Build a lookup of quests_by_date from both the prop and the calendar API
  const questsByDateLookup = useMemo<Record<string, CalendarQuest[]>>(() => {
    const lookup: Record<string, CalendarQuest[]> = {};
    if (questsByDateProp) {
      questsByDateProp.forEach((g) => {
        lookup[g.date] = g.quests;
      });
    }
    return lookup;
  }, [questsByDateProp]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [scheduleEvents, questList, missionList, calendarData] = await Promise.all([
        endpoints.schedule.list(),
        endpoints.quests.list().catch(() => [] as Quest[]),
        endpoints.missions.list().catch(() => [] as Mission[]),
        endpoints.questCentre.calendar().catch(() => null as QuestCentreCalendar | null),
      ]);

      // Merge quests_by_date from API and prop
      const mergedLookup: Record<string, CalendarQuest[]> = { ...questsByDateLookup };
      if (calendarData?.quests_by_date) {
        calendarData.quests_by_date.forEach((g) => {
          mergedLookup[g.date] = g.quests;
        });
      }

      const mapped: CalendarEvent[] = [
        ...scheduleEvents.map((e) => ({ ...e, type: 'schedule' as const, source_id: e.id })),
        ...questList
          .filter((q) => q.due_date && q.status !== 'Completed')
          .map((q) => {
            const d = new Date(q.due_date!);
            return {
              id: `quest-${q.id}`,
              title: q.title,
              day_of_week: dateToDayOfWeek(d),
              start_time: null,
              end_time: null,
              reference_type: 'quest' as const,
              color: '#ff9800',
              type: 'quest' as const,
              source_id: q.id,
              due_date: q.due_date!,
            };
          }),
        ...missionList
          .filter((m) => m.due_date && m.status !== 'Completed')
          .map((m) => {
            const d = new Date(m.due_date!);
            return {
              id: `mission-${m.id}`,
              title: m.title,
              day_of_week: dateToDayOfWeek(d),
              start_time: null,
              end_time: null,
              reference_type: 'mission' as const,
              color: '#4caf50',
              type: 'mission' as const,
              source_id: m.id,
              due_date: m.due_date!,
            };
          }),
      ];

      // Add quests from mergedLookup that are not already in mapped
      Object.entries(mergedLookup).forEach(([dateStr, quests]) => {
        const d = new Date(dateStr + 'T00:00:00');
        const dow = dateToDayOfWeek(d);
        quests.forEach((q) => {
          const exists = mapped.some(
            (e) => e.type === 'quest' && e.source_id === q.id,
          );
          if (!exists) {
            mapped.push({
              id: `quest-${q.id}`,
              title: q.title,
              day_of_week: dow,
              start_time: null,
              end_time: null,
              reference_type: 'quest' as const,
              color: '#ff9800',
              type: 'quest' as const,
              source_id: q.id,
              due_date: dateStr,
            });
          }
        });
      });

      setEvents(mapped);
    } catch {
      // errors already caught per-endpoint
    } finally {
      setLoading(false);
    }
  }, [questsByDateLookup]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const dayDates = useMemo(() => getDayDates(weekStart), [weekStart]);

  const goBack = useCallback(() => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    setWeekStart(d);
  }, [weekStart]);

  const goForward = useCallback(() => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    setWeekStart(d);
  }, [weekStart]);

  const goToday = useCallback(() => {
    setWeekStart(getWeekRange(new Date()).start);
  }, []);

  const getEventsForDay = useCallback(
    (dayIndex: number): CalendarEvent[] =>
      events.filter((e) => e.day_of_week === dayIndex),
    [events],
  );

  const getQuestsForDate = useCallback(
    (date: Date): CalendarQuest[] => {
      const dateStr = format(date, 'yyyy-MM-dd');
      return events
        .filter((e) => e.type === 'quest' && e.due_date === dateStr)
        .map((e) => ({
          id: e.source_id ?? 0,
          title: e.title,
          status: 'active',
          priority: null as string | null,
          category: null as string | null,
          xp_reward: 0,
        }));
    },
    [events],
  );

  // ── Quick-create ──
  const openQuickCreate = useCallback((dayIndex: number) => {
    setCreatingDayIndex(dayIndex);
    setQuickTitle('');
    setQuickStart('');
    setQuickEnd('');
  }, []);

  const cancelQuickCreate = useCallback(() => {
    setCreatingDayIndex(null);
  }, []);

  const submitQuickCreate = useCallback(
    async (dayIndex: number) => {
      if (!quickTitle.trim()) return;
      try {
        await endpoints.schedule.create({
          title: quickTitle.trim(),
          day_of_week: dayIndex,
          start_time: quickStart || null,
          end_time: quickEnd || null,
          reference_type: null,
          color: '#9c27b0',
        });
        setCreatingDayIndex(null);
        await fetchAll();
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : 'Failed to create event');
      }
    },
    [quickTitle, quickStart, quickEnd, fetchAll],
  );

  // ── Drag-to-reschedule ──
  const handleDragStart = useCallback(
    (e: React.DragEvent, ev: CalendarEvent) => {
      if (ev.type !== 'schedule') {
        e.preventDefault();
        return;
      }
      setDragId(`${ev.source_id}`);
      e.dataTransfer.setData('text/plain', `${ev.source_id}`);
      e.dataTransfer.effectAllowed = 'move';
    },
    [],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent, targetDay: number) => {
      e.preventDefault();
      const rawId = e.dataTransfer.getData('text/plain');
      if (!rawId) return;
      const id = parseInt(rawId, 10);
      if (isNaN(id)) return;
      setDragId(null);
      try {
        await endpoints.schedule.update(id, { day_of_week: targetDay });
        await fetchAll();
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : 'Failed to move event');
      }
    },
    [fetchAll],
  );

  // ── Event chip renderer ──
  const renderEventChip = useCallback(
    (ev: CalendarEvent) => {
      const color = ev.color || typeColors[ev.reference_type || ''] || '#707070';
      return (
        <div
          key={ev.id}
          draggable={ev.type === 'schedule'}
          onDragStart={(e) => handleDragStart(e, ev)}
          style={{
            fontSize: '0.6rem',
            padding: '3px 5px',
            borderRadius: 4,
            background: `${color}22`,
            borderLeft: `3px solid ${color}`,
            color: '#ddd',
            fontFamily: 'monospace',
            cursor: ev.type === 'schedule' ? 'grab' : 'default',
            opacity: dragId === `${ev.source_id}` ? 0.4 : 1,
            transition: 'opacity 0.15s',
          }}
          title={
            ev.type === 'schedule'
              ? `Drag to move • ${ev.reference_type ? `Type: ${ev.reference_type}` : 'Manual entry'}`
              : `Due this day • ${ev.type}`
          }
        >
          {ev.start_time && (
            <span style={{ color: '#888', marginRight: 4 }}>
              {ev.start_time.slice(0, 5)}
            </span>
          )}
          {ev.title}
        </div>
      );
    },
    [dragId, handleDragStart],
  );

  // ── Quick-create form ──
  const renderQuickForm = useCallback(
    (dayIndex: number) => {
      if (creatingDayIndex !== dayIndex) return null;
      return (
        <div
          style={{
            marginTop: 6,
            padding: 6,
            background: '#1a1a1a',
            borderRadius: 4,
            border: '1px solid #3a3a3a',
          }}
        >
          <input
            type="text"
            placeholder="Event title..."
            value={quickTitle}
            onChange={(e) => setQuickTitle(e.target.value)}
            style={inputStyle}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') submitQuickCreate(dayIndex);
              if (e.key === 'Escape') cancelQuickCreate();
            }}
          />
          <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
            <input
              type="time"
              value={quickStart}
              onChange={(e) => setQuickStart(e.target.value)}
              style={{ ...inputStyle, width: '50%' }}
              placeholder="Start"
            />
            <input
              type="time"
              value={quickEnd}
              onChange={(e) => setQuickEnd(e.target.value)}
              style={{ ...inputStyle, width: '50%' }}
              placeholder="End"
            />
          </div>
          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
            <RpgButton variant="ghost" size="sm" onClick={cancelQuickCreate}>
              Cancel
            </RpgButton>
            <RpgButton
              variant="orange"
              size="sm"
              onClick={() => submitQuickCreate(dayIndex)}
              disabled={!quickTitle.trim()}
            >
              Add
            </RpgButton>
          </div>
        </div>
      );
    },
    [creatingDayIndex, quickTitle, quickStart, quickEnd, submitQuickCreate, cancelQuickCreate],
  );

  // ── Day column renderer (week view) ──
  const renderDayColumn = useCallback(
    (date: Date, i: number) => {
      const dayEvents = getEventsForDay(i);
      const today = isToday(date);
      const questsForDay = getQuestsForDate(date);
      const allItems = [...dayEvents, ...questsForDay.map((q) => ({
        id: `quest-${q.id}`,
        title: q.title,
        day_of_week: i,
        start_time: null as string | null,
        end_time: null as string | null,
        reference_type: 'quest' as const,
        color: '#ff9800',
        type: 'quest' as const,
        source_id: q.id,
        due_date: undefined as string | undefined,
      }))];
      const isExpanded = expandedDay === i;
      return (
        <RpgCard
          key={i}
          style={{
            padding: '10px',
            minHeight: viewMode === 'week' ? 120 : undefined,
            borderColor: today ? 'var(--rpg-accent-orange)' : undefined,
            boxShadow: today ? '0 0 12px rgba(255,152,0,0.2)' : undefined,
          }}
        >
          <div
            style={{
              textAlign: 'center',
              marginBottom: '8px',
              paddingBottom: '6px',
              borderBottom: '1px solid #2a2a2a',
              cursor: 'pointer',
            }}
            onClick={() => {
              setExpandedDay(isExpanded ? null : i);
            }}
          >
            <div
              style={{
                fontSize: '0.7rem',
                color: today ? '#ff9800' : '#b0b0b0',
                fontFamily: 'monospace',
                fontWeight: 600,
              }}
            >
              {DAY_NAMES[i]}
            </div>
            <div
              style={{
                fontSize: '0.85rem',
                color: today ? '#fff' : '#b0b0b0',
                fontFamily: 'monospace',
                marginTop: '2px',
              }}
            >
              {date.getDate()}
            </div>
          </div>
          {isExpanded && (
            <div
              style={{
                fontSize: '0.65rem',
                color: '#ccc',
                fontFamily: 'monospace',
                marginBottom: 4,
                padding: '4px 6px',
                background: '#1a1a1a',
                borderRadius: 4,
                border: '1px solid #2a2a2a',
              }}
            >
              {allItems.length === 0
                ? 'No quests or events'
                : allItems.map((ev) => (
                    <div key={ev.id} style={{ padding: '2px 0', borderBottom: '1px solid #222' }}>
                      <span style={{ color: ev.color ?? '#ff9800', fontWeight: 600 }}>
                        {ev.type === 'quest' ? '⚔' : ev.type === 'mission' ? '🎯' : '📋'}
                      </span>{' '}
                      {ev.title}
                    </div>
                  ))}
            </div>
          )}
          <div
            style={{ display: 'flex', flexDirection: 'column', gap: '4px', minHeight: 40 }}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, i)}
            onClick={(e) => {
              if ((e.target as HTMLElement).closest('[draggable]')) return;
              if (isExpanded) {
                setExpandedDay(null);
              } else {
                openQuickCreate(i);
              }
            }}
          >
            {allItems.length === 0 && creatingDayIndex !== i && !isExpanded && (
              <span
                style={{
                  fontSize: '0.6rem',
                  color: '#505050',
                  textAlign: 'center',
                  fontFamily: 'monospace',
                  marginTop: 8,
                }}
              >
                + click to add
              </span>
            )}
            {allItems.map(renderEventChip)}
            {renderQuickForm(i)}
          </div>
        </RpgCard>
      );
    },
    [
      getEventsForDay,
      getQuestsForDate,
      viewMode,
      openQuickCreate,
      handleDragOver,
      handleDrop,
      renderEventChip,
      renderQuickForm,
      expandedDay,
      creatingDayIndex,
    ],
  );

  // ── Month grid renderer ──
  const renderMonthGrid = useCallback(() => {
    const today = new Date();
    const currentMonth = today.getMonth();
    const currentYear = today.getFullYear();

    return (
      <div>
        <div className="qc-month-grid">
          {MONTH_DOW.map((d) => (
            <div key={d} className="qc-month-dow">{d}</div>
          ))}
          {monthDays.map((date, i) => {
            if (!date) {
              return <div key={`empty-${i}`} className="qc-month-day other" />;
            }
            const isTodayDate = isToday(date);
            const isCurrentMonth = date.getMonth() === currentMonth && date.getFullYear() === currentYear;
            const quests = getQuestsForDate(date);
            const hasQuests = quests.length > 0;
            return (
              <div
                key={format(date, 'yyyy-MM-dd')}
                className={[
                  'qc-month-day',
                  !isCurrentMonth ? 'other' : '',
                  isTodayDate ? 'today' : '',
                  hasQuests ? 'has-quests' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => {
                  setViewMode('week');
                  setWeekStart(getWeekRange(date).start);
                }}
              >
                <div
                  style={{
                    fontSize: '0.65rem',
                    color: isTodayDate ? '#ff9800' : '#b0b0b0',
                    fontFamily: 'monospace',
                    fontWeight: 600,
                    textAlign: 'right',
                    paddingRight: 2,
                  }}
                >
                  {date.getDate()}
                </div>
                {hasQuests && (
                  <div style={{ marginTop: 2 }}>
                    {quests.slice(0, 3).map((q) => (
                      <div
                        key={q.id}
                        style={{
                          fontSize: '0.55rem',
                          padding: '1px 3px',
                          borderRadius: 2,
                          background: 'var(--qc-gold)',
                          color: '#121212',
                          fontFamily: 'monospace',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          cursor: 'pointer',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/schedule');
                        }}
                      >
                        {q.title}
                      </div>
                    ))}
                    {quests.length > 3 && (
                      <div style={{ fontSize: '0.5rem', color: 'var(--text-muted)', fontFamily: 'monospace', textAlign: 'center' }}>
                        +{quests.length - 3} more
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <Link to="/schedule" className="qc-cal-open-link">
          Open in Calendar →
        </Link>
      </div>
    );
  }, [monthDays, getQuestsForDate, navigate]);

  // ── Week view content ──
  const renderWeekView = useCallback(() => {
    const allQuestsForWeek = events.filter((e) => e.type === 'quest' || e.type === 'mission');
    return (
      <div style={{ overflowX: 'auto' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '8px',
            minWidth: '700px',
          }}
        >
          {dayDates.map((date, i) => renderDayColumn(date, i))}
        </div>
        {allQuestsForWeek.length === 0 && (
          <div className="qc-empty-pixel">
            <span className="qc-empty-icon">📭</span>
            <p>No quests or events scheduled this week.</p>
            <p style={{ fontSize: '0.6rem', color: '#666', fontFamily: 'monospace' }}>
              Click on any day column to add an event.
            </p>
            <Link to="/schedule" className="qc-cal-open-link">
              Open in Calendar →
            </Link>
          </div>
        )}
      </div>
    );
  }, [dayDates, renderDayColumn, events]);

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <h2 style={{ fontFamily: 'monospace', color: '#fff', margin: 0 }}>
          📅 Weekly Calendar
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Week/Month tab bar */}
          <div className="qc-cal-tabs">
            <button
              className={`qc-cal-tab${viewMode === 'week' ? ' active' : ''}`}
              onClick={() => setViewMode('week')}
            >
              Week
            </button>
            <button
              className={`qc-cal-tab${viewMode === 'month' ? ' active' : ''}`}
              onClick={() => setViewMode('month')}
            >
              Month
            </button>
          </div>
          {viewMode === 'week' && (
            <>
              <RpgButton variant="ghost" size="sm" onClick={goBack}>
                ◀
              </RpgButton>
              <span
                style={{
                  color: '#b0b0b0',
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                  minWidth: 120,
                  textAlign: 'center',
                }}
              >
                {formatDate(dayDates[0])} — {formatDate(dayDates[6])}
              </span>
              <RpgButton variant="ghost" size="sm" onClick={goForward}>
                ▶
              </RpgButton>
              <RpgButton variant="orange" size="sm" onClick={goToday}>
                Today
              </RpgButton>
            </>
          )}
          {viewMode === 'month' && (
            <>
              <RpgButton variant="ghost" size="sm" onClick={() => setMonthOffset((o) => o - 1)}>
                ◀
              </RpgButton>
              <span
                style={{
                  color: '#b0b0b0',
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                  minWidth: 120,
                  textAlign: 'center',
                }}
              >
                {format(monthStart, 'MMMM yyyy')}
              </span>
              <RpgButton variant="ghost" size="sm" onClick={() => setMonthOffset((o) => o + 1)}>
                ▶
              </RpgButton>
            </>
          )}
          <Link to="/schedule" className="qc-cal-open-link">
            Open in Calendar →
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="rpg-empty">
          <p className="rpg-empty-text">Loading schedule...</p>
        </div>
      ) : viewMode === 'week' ? (
        renderWeekView()
      ) : (
        <div style={{ overflowX: 'auto' }}>
          {renderMonthGrid()}
        </div>
      )}
    </div>
  );
};
