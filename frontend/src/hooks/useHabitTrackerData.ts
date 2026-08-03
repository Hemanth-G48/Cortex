import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import { toIso } from '../utils/vaultDates';
import type {
  Habit,
  HabitCalendarDay,
  HabitTrackerStatusWindow,
  HabitTrackerSummary,
  HabitTodayItem,
  ProgressReport,
} from '../services/api';

export interface HabitTrackerData {
  statusWindow: HabitTrackerStatusWindow | null;
  summary: HabitTrackerSummary | null;
  progress: ProgressReport | null;
  goodHabits: Habit[];
  badHabits: Habit[];
  todayItems: HabitTodayItem[];
  /** Current-week calendar feeds the Overview tabs (Phases 73/81). */
  goodCalendar: HabitCalendarDay[];
  badCalendar: HabitCalendarDay[];
}

export interface HabitTrackerHook {
  data: HabitTrackerData;
  loading: boolean;
  errors: string[];
  refresh: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<HabitTrackerData>>;
}

const EMPTY: HabitTrackerData = {
  statusWindow: null,
  summary: null,
  progress: null,
  goodHabits: [],
  badHabits: [],
  todayItems: [],
  goodCalendar: [],
  badCalendar: [],
};

/** Monday-first ISO range covering the current week. */
const weekRange = (): { start: string; end: string } => {
  const now = new Date();
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  const diff = d.getDay() === 0 ? -6 : 1 - d.getDay();
  d.setDate(d.getDate() + diff);
  const end = new Date(d);
  end.setDate(d.getDate() + 6);
  return { start: toIso(d), end: toIso(end) };
};

/**
 * Fetch every Gamified Habit Tracker payload in parallel (Phase 61):
 * status-window + summary + progress bars + good/bad habits + Did-Today +
 * current-week calendars (for the overview tabs). Row 4/5 calendar widgets
 * fetch their own navigable ranges via HtCompletedCalendar.
 */
export const useHabitTrackerData = (): HabitTrackerHook => {
  const [data, setData] = useState<HabitTrackerData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    const errs: string[] = [];
    const { start, end } = weekRange();
    const [sw, sum, prog, good, bad, today, goodCal, badCal] = await Promise.allSettled([
      endpoints.habitTracker.statusWindow(),
      endpoints.habitTracker.summary(),
      endpoints.questCentre.progress(),
      endpoints.habits.good(),
      endpoints.habits.bad(),
      endpoints.habits.today(),
      endpoints.habits.calendar('good', start, end),
      endpoints.habits.calendar('bad', start, end),
    ]);
    const ok = <T,>(r: PromiseSettledResult<T>): T | null => (r.status === 'fulfilled' ? r.value : null);
    if (sw.status === 'rejected') errs.push('status-window');
    if (sum.status === 'rejected') errs.push('summary');
    if (prog.status === 'rejected') errs.push('progress');
    if (good.status === 'rejected') errs.push('good-habits');
    if (bad.status === 'rejected') errs.push('bad-habits');
    if (today.status === 'rejected') errs.push('today');
    if (goodCal.status === 'rejected') errs.push('good-calendar');
    if (badCal.status === 'rejected') errs.push('bad-calendar');
    setData({
      statusWindow: ok(sw),
      summary: ok(sum),
      progress: ok(prog),
      goodHabits: ok(good) ?? [],
      badHabits: ok(bad) ?? [],
      todayItems: ok(today) ?? [],
      goodCalendar: ok(goodCal) ?? [],
      badCalendar: ok(badCal) ?? [],
    });
    setErrors(errs);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, errors, refresh, setData };
};
