import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { Header } from '../components/layout/Header';
import { teacherApi } from '../services/api';
import type { TeacherStudent } from '../services/api';
import { StudentList } from '../components/teacher/StudentList';
import { BroadcastHub } from '../components/teacher/BroadcastHub';
import { StudentDetailModal } from '../components/teacher/StudentDetailModal';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';

export const Teacher = () => {
  const { role } = useAuth();
  const { toast } = useToast();
  const [students, setStudents] = useState<TeacherStudent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detailId, setDetailId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await teacherApi.students();
      setStudents(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load students');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleToggle = useCallback((id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleToggleAll = useCallback(() => {
    setSelected((prev) => {
      if (prev.size === students.length) return new Set<number>();
      return new Set(students.map((s) => s.id));
    });
  }, [students]);

  const handleOpenDetail = useCallback((id: number) => {
    setDetailId(id);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setDetailId(null);
  }, []);

  const handleBroadcastDone = useCallback(() => {
    setSelected(new Set());
    toast('Broadcast sent successfully', 'success');
    void refresh();
  }, [toast, refresh]);

  if (role !== 'teacher') {
    return (
      <div className="page-section">
        <Header title="Teacher Dashboard" />
        <div className="card empty-state">
          <div className="empty-icon">🔒</div>
          <div className="empty-title">Access denied</div>
          <div className="empty-message">You must be a teacher to view this page.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-section fade-in">
      <Header title="Teacher Dashboard" />
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        Manage your students, view their progress, and broadcast content.
      </p>

      {loading && (
        <div className="card-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {error && (
        <div className="card" style={{ borderColor: 'var(--danger)', padding: '1rem', marginBottom: '1rem' }}>
          <p style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>{error}</p>
          <button type="button" className="btn btn-secondary" style={{ marginTop: '0.5rem' }} onClick={() => void refresh()}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && students.length === 0 && (
        <EmptyState icon="👥" title="No students" message="No students are enrolled in your courses yet." />
      )}

      {!loading && !error && students.length > 0 && (
        <>
          <StudentList
            students={students}
            selected={selected}
            onToggle={handleToggle}
            onToggleAll={handleToggleAll}
            onOpenDetail={handleOpenDetail}
          />

          <BroadcastHub selected={Array.from(selected)} onDone={handleBroadcastDone} />
        </>
      )}

      <StudentDetailModal studentId={detailId} onClose={handleCloseDetail} />
    </div>
  );
};
