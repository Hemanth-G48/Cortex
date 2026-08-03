/** Vault date helpers shared by heatmap / streak grid components. */

export interface LogEntry {
  date: string; // ISO yyyy-mm-dd
  completed?: boolean;
  count?: number;
}

/** Build the last `size` days as ISO date strings ending today (exclusive of today if excludeToday). */
export function lastNDays(size: number, excludeToday = false): string[] {
  const days: string[] = [];
  const start = new Date();
  if (excludeToday) start.setDate(start.getDate() - 1);
  for (let i = size - 1; i >= 0; i--) {
    const d = new Date(start);
    d.setDate(start.getDate() - i);
    days.push(toIso(d));
  }
  return days;
}

export function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Quick lookup: date string -> log entry (first match wins). */
export function mapLogs(logs: LogEntry[]): Map<string, LogEntry> {
  const m = new Map<string, LogEntry>();
  for (const l of logs) m.set(l.date, l);
  return m;
}
