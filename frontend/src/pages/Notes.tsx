import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Note, Course } from '../services/api';

export const Notes = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    endpoints.notes.list().then(setNotes).catch(() => {});
    endpoints.courses.list().then(setCourses).catch(() => {});
  }, []);

  const courseName = (cid: number) => courses.find((c) => c.id === cid)?.title ?? '—';

  return (
    <div>
      <Header title="Notes" />
      <div className="card-grid">
        {notes.map((n) => (
          <div className="card" key={n.id}>
            <h3 style={{ marginBottom: '0.25rem' }}>{n.title}</h3>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              {courseName(n.course_id)} · {n.created_date}
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineClamp: 3, WebkitLineClamp: 3, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {n.content ?? 'No content'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
