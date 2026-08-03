import { format, formatDistanceToNow, isToday, isTomorrow } from 'date-fns';

/** Safely parse a date-or-time value to a Date (returns null if unparseable) */
const safeParse = (d: Date | string): Date | null => {
  if (d instanceof Date && !isNaN(d.getTime())) return d;
  if (typeof d !== 'string') return null;

  // time-only string ("09:00:00" or "14:30")
  const timeMatch = d.match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
  if (timeMatch) {
    const date = new Date();
    date.setHours(+timeMatch[1], +timeMatch[2], +(timeMatch[3] ?? 0), 0);
    return date;
  }

  // full date string
  const parsed = new Date(d);
  return isNaN(parsed.getTime()) ? null : parsed;
};

/** Format time as "HH:MM". Handles time-only strings like "09:00:00". */
export const formatTime = (d: Date | string): string => {
  const date = safeParse(d);
  if (!date) return String(d);
  return format(date, 'HH:mm');
};

/** Format date as "Mon, Jan 1" */
export const formatDate = (d: Date | string): string => {
  const date = safeParse(d);
  if (!date) return String(d);
  return format(date, 'EEE, MMM d');
};

/** Human-friendly relative string */
export const relativeDate = (d: Date | string): string => {
  const date = safeParse(d);
  if (!date) return String(d);
  if (isToday(date)) return 'Today';
  if (isTomorrow(date)) return 'Tomorrow';
  return formatDistanceToNow(date, { addSuffix: true });
};

/** Days until a date string (negative if past) */
export const getDaysUntil = (dateStr: string): number => {
  const target = new Date(dateStr);
  const now = new Date();
  target.setHours(0, 0, 0, 0);
  now.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - now.getTime()) / 86400000);
};

/** Return a colour variable based on priority */
export const getPriorityColor = (priority: string): string => {
  switch ((priority ?? '').toLowerCase()) {
    case 'high': return 'var(--danger)';
    case 'medium': return 'var(--warning)';
    case 'low': return 'var(--text-muted)';
    default: return 'var(--text-secondary)';
  }
};
