import { useEffect, useMemo, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonTable } from '../components/shared/Skeleton';
import type { Course, ScheduleEvent } from '../services/api';
import { TimetableGrid } from '../components/timetable/TimetableGrid';

export const Schedule = () => {
  const [searchParams] = useSearchParams();
  const [entries, setEntries] = useState<ScheduleEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', day_of_week: 1, start_time: '09:00', end_time: '10:00', event_type: 'class', location: '' });
  // Defect #59: course blocks are colour-coded from their vault course/domain
  // colours, so the timetable reflects the Second Brain's folder hierarchy.
  const [courses, setCourses] = useState<Course[]>([]);
  const [domainColors, setDomainColors] = useState<Record<number, string>>({});

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const day = searchParams.get('day_of_week');
    endpoints.schedule.list(day !== null ? Number(day) : undefined)
      .then(setEntries)
      // Defect #30 fix: surface load failures.
      .catch(() => setError('Could not load schedule — is the backend running?'))
      .finally(() => setLoading(false));
  }, [searchParams]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    endpoints.courses.list().then(setCourses).catch(() => setCourses([]));
  }, []);

  // Courses without a stored colour fall back to their first vault domain's
  // colour (GET /courses/{id}/content → second_brain.domains[].color).
  useEffect(() => {
    const missing = courses.filter((c) => !c.color && c.kb_folder_path);
    if (missing.length === 0) return;
    let stale = false;
    Promise.all(
      missing.map((c) =>
        endpoints.courses
          .content(c.id)
          .then((content) => {
            const domain = content.second_brain?.domains?.find((d) => d.color);
            return domain?.color ? ([c.id, domain.color] as const) : null;
          })
          .catch(() => null),
      ),
    ).then((rows) => {
      if (stale) return;
      const next: Record<number, string> = {};
      for (const row of rows) {
        if (row) next[row[0]] = row[1];
      }
      setDomainColors(next);
    });
    return () => {
      stale = true;
    };
  }, [courses]);

  const courseColor = useCallback(
    (course: Course) => course.color ?? domainColors[course.id] ?? null,
    [domainColors],
  );

  // Enrich entries with their course's domain colour (title or folder match);
  // entries that do not map to a course keep whatever colour they already had.
  const coloredEntries = useMemo(() => {
    if (courses.length === 0) return entries;
    const byTitle = new Map<string, Course>();
    for (const c of courses) {
      byTitle.set(c.title.trim().toLowerCase(), c);
      const folder = c.kb_folder_path?.split(/[\\/]/).filter(Boolean).pop();
      if (folder) byTitle.set(folder.trim().toLowerCase(), c);
    }
    const byId = new Map(courses.map((c) => [c.id, c]));
    return entries.map((e) => {
      const linked =
        e.reference_type === 'course' && e.reference_id != null
          ? byId.get(e.reference_id)
          : undefined;
      const course = linked ?? byTitle.get(e.title.trim().toLowerCase());
      const color = course ? courseColor(course) : null;
      return color ? { ...e, color } : e;
    });
  }, [entries, courses, courseColor]);

  // Defect #29/#81 fix: event creation from this page.
  const handleCreate = async () => {
    if (!form.title.trim()) return;
    try {
      await endpoints.schedule.create({
        title: form.title.trim(),
        day_of_week: Number(form.day_of_week),
        start_time: form.start_time,
        end_time: form.end_time,
        event_type: form.event_type || undefined,
        location: form.location || undefined,
      });
      setForm({ title: '', day_of_week: 1, start_time: '09:00', end_time: '10:00', event_type: 'class', location: '' });
      setShowCreate(false);
      load();
    } catch {
      setError('Could not create the event');
    }
  };

  const handleDelete = (id: number) => {
    if (!confirmDelete('this schedule event')) return;
    endpoints.schedule.delete(id).then(load).catch(() => setError('Could not delete the event'));
  };

  return (
    <div>
      <Header title="Schedule" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? '− Cancel' : '+ New Event'}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Event title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <select value={form.day_of_week} onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })} style={{ width: 'auto' }}>
              <option value={1}>Monday</option>
              <option value={2}>Tuesday</option>
              <option value={3}>Wednesday</option>
              <option value={4}>Thursday</option>
              <option value={5}>Friday</option>
              <option value={6}>Saturday</option>
              <option value={7}>Sunday</option>
            </select>
            <input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} style={{ width: 120 }} />
            <span style={{ alignSelf: 'center' }}>→</span>
            <input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} style={{ width: 120 }} />
            <select value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })} style={{ width: 'auto' }}>
              <option value="class">Class</option>
              <option value="work">Work</option>
              <option value="health">Health</option>
              <option value="social">Social</option>
              <option value="other">Other</option>
            </select>
            <button type="button" className="btn btn-primary" onClick={() => void handleCreate()} disabled={!form.title.trim()}>Create</button>
          </div>
          <input placeholder="Location (optional)" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="card">
        {loading ? (
          SkeletonTable(6)
        ) : entries.length === 0 ? (
          <EmptyState
            icon="🗓"
            title="No events scheduled"
            message="Add your first schedule event to build a weekly timetable."
            action={<button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Event</button>}
          />
        ) : (
          <>
            <TimetableGrid entries={coloredEntries} />
            <div className="card" style={{ marginTop: '1rem' }}>
              <table className="data-table">
                <thead><tr><th>Event</th><th>Time</th><th>Description</th><th></th></tr></thead>
                <tbody>
                  {entries.map((e) => (
                    <tr key={e.id}>
                      <td>{e.title}</td>
                      <td>{e.start_time}–{e.end_time}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{e.location ?? e.event_type ?? '—'}</td>
                      <td>
                        <button onClick={() => handleDelete(e.id)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.75rem' }}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
