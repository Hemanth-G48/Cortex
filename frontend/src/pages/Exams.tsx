import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { SkeletonTable } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { Exam, Course } from '../services/api';

export const Exams = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', course_id: 0, date: '' });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      endpoints.exams.list().catch(() => null),
      endpoints.courses.list().catch(() => null),
    ]).then(([es, cs]) => {
      if (es === null && cs === null) {
        // Defect #86 fix: surface load failures instead of an empty page.
        setError('Could not load exams — is the backend running?');
        return;
      }
      setExams(es ?? []);
      setCourses(cs ?? []);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Defect #36 fix: exam creation from this page.
  const handleCreate = async () => {
    if (!form.title.trim() || !form.course_id) return;
    try {
      await endpoints.exams.create({
        title: form.title.trim(),
        course_id: Number(form.course_id),
        date: form.date || undefined,
      });
      setForm({ title: '', course_id: 0, date: '' });
      setShowCreate(false);
      load();
    } catch {
      setError('Could not create the exam');
    }
  };

  const courseName = (cid: number) => courses.find((c) => c.id === cid)?.title ?? '—';

  return (
    <div>
      <Header title="Exams" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)} disabled={courses.length === 0}>
          {showCreate ? '− Cancel' : '+ New Exam'}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Exam title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <select value={form.course_id} onChange={(e) => setForm({ ...form, course_id: Number(e.target.value) })} style={{ width: 'auto' }}>
              <option value={0} disabled>Select course</option>
              {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
            <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} style={{ width: 170 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleCreate()} disabled={!form.title.trim() || !form.course_id}>Create</button>
          </div>
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
          SkeletonTable(5)
        ) : exams.length === 0 ? (
          <EmptyState
            icon="📝"
            title="No exams yet"
            message="Add an exam to track what's coming up."
            action={courses.length > 0 ? <button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Exam</button> : undefined}
          />
        ) : (
          <table className="data-table">
            <thead><tr><th>Exam</th><th>Course</th><th>Date</th><th>Status</th></tr></thead>
            <tbody>
              {exams.map((e) => (
                <tr key={e.id}>
                  <td>{e.title}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{courseName(e.course_id)}</td>
                  <td style={{ fontSize: '0.8rem' }}>{e.date}</td>
                  <td><span className={`badge badge-${e.status === 'Completed' ? 'success' : 'info'}`}>{e.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
