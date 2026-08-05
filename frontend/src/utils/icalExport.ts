// iCal export (99-phase plan, Phase 13 — ported from Shiori-v1 `utils/icalExport.js`).
const pad = (n: number) => String(n).padStart(2, '0');

const toISOBasic = (date: Date) =>
  `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}T${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(date.getUTCSeconds())}Z`;

const escapeICS = (str: string | null | undefined) =>
  String(str ?? '')
    .replace(/[\\;,]/g, (c) => '\\' + c)
    .replace(/\n/g, '\\n');

export interface ICalAssignment {
  id: number | string;
  title: string;
  description?: string | null;
  courseName?: string | null;
  due_date: string;
  status?: string;
}

export const exportAssignmentsToICal = (assignments: ICalAssignment[], appName = 'Student Life OS') => {
  const now = toISOBasic(new Date());
  const pending = assignments.filter((a) => a.status !== 'Completed');

  const events = pending.map((a) => {
    const due = new Date(a.due_date);
    due.setHours(23, 59, 0, 0);
    const dtstart = toISOBasic(due);

    return [
      'BEGIN:VEVENT',
      `UID:slos-${a.id}@student-life-os`,
      `DTSTAMP:${now}`,
      `DTSTART:${dtstart}`,
      `DTEND:${dtstart}`,
      `SUMMARY:${escapeICS(a.title)}`,
      `DESCRIPTION:${escapeICS(`${a.courseName ?? ''} — ${a.description ?? ''}`)}`,
      'END:VEVENT',
    ].join('\r\n');
  });

  const ics = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    `PRODID:-//${appName}//Deadlines//EN`,
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    `X-WR-CALNAME:${appName} Deadlines`,
    'X-WR-TIMEZONE:UTC',
    ...events,
    'END:VCALENDAR',
  ].join('\r\n');

  const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `slos-deadlines-${new Date().toISOString().split('T')[0]}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
