import { useEffect, useState } from 'react';
import { teacherApi } from '../../services/api';
import type { TeacherStudentDetail } from '../../services/api';

interface StudentDetailModalProps {
  studentId: number | null;
  onClose: () => void;
}

export const StudentDetailModal = ({ studentId, onClose }: StudentDetailModalProps) => {
  const [detail, setDetail] = useState<TeacherStudentDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (studentId === null) return;
    setLoading(true);
    setError('');
    teacherApi
      .studentDetail(studentId)
      .then(setDetail)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load details'))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (studentId === null) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(600px, 92vw)' }}>
        <h2 className="modal-title">Student Details</h2>

        {loading && <div className="card"><p style={{ textAlign: 'center', padding: '1rem' }}>Loading…</p></div>}

        {error && (
          <div className="card" style={{ borderColor: 'var(--danger)', padding: '1rem', marginBottom: '1rem' }}>
            <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>
          </div>
        )}

        {detail && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Assignments */}
            <div>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>Assignments</h3>
              {detail.assignments.length === 0 ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No assignments.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {detail.assignments.map((a) => (
                    <li key={a.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0.5rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.8rem' }}>
                      <span>{a.title}</span>
                      <span className="badge badge-info">{a.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Todos */}
            <div>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>Todos</h3>
              {detail.todos.length === 0 ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No todos.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {detail.todos.map((t) => (
                    <li key={t.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0.5rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.8rem' }}>
                      <span>{t.title}</span>
                      <span className="badge badge-info">{t.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Brain dump */}
            <div>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>Brain Dump</h3>
              {detail.braindump === null ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No brain dump</p>
              ) : detail.braindump.content ? (
                <p style={{ fontSize: '0.8rem', background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: 'var(--radius)', whiteSpace: 'pre-wrap' }}>
                  {detail.braindump.content}
                </p>
              ) : (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Empty brain dump</p>
              )}
            </div>

            {/* Books */}
            <div>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>Books</h3>
              {detail.books.length === 0 ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No books.</p>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {detail.books.map((b) => (
                    <li key={b.id} style={{ padding: '0.35rem 0.5rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', fontSize: '0.8rem' }}>
                      <strong>{b.title}</strong>{b.author ? ` by ${b.author}` : ''} · <span className="badge badge-info">{b.category}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        <div className="modal-actions" style={{ marginTop: '1rem' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};
