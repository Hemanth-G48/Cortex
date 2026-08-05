import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import type { QuizHistoryItem } from '../../services/api';
import { EmptyState } from '../shared/EmptyState';
import { SkeletonTable } from '../shared/Skeleton';

interface QuizHistoryProps {
  /** Bump to refetch (e.g. after a new attempt is scored). */
  reloadKey?: number;
}

/** Past quiz attempts with score badges (plan Phase 69). */
export const QuizHistory = ({ reloadKey }: QuizHistoryProps) => {
  const [history, setHistory] = useState<QuizHistoryItem[] | null>(null);

  const load = useCallback(() => {
    endpoints.quizzes.history().then(setHistory).catch(() => setHistory([]));
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  if (history === null) return <>{SkeletonTable(2)}</>;

  if (history.length === 0) {
    return <EmptyState icon="🧠" title="No quiz attempts yet" message="Generate a quiz above — your scores will show here." />;
  }

  return (
    <div style={{ display: 'grid', gap: '0.5rem' }}>
      {history.map((h) => {
        const pct = h.total_questions ? Math.round(((h.score ?? 0) / h.total_questions) * 100) : null;
        const color = pct != null && pct >= 80 ? 'var(--success)' : pct != null && pct >= 50 ? 'var(--warning)' : 'var(--danger)';
        return (
          <div
            key={h.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
              padding: '0.7rem 0.9rem',
              borderRadius: 'var(--radius)',
              background: 'var(--bg-hover)',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Quiz #{h.quiz_id}
              {h.created_at && <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>{new Date(h.created_at).toLocaleDateString()}</span>}
            </div>
            {pct != null ? (
              <span className="badge" style={{ color, background: `${color}1a` }}>{h.score}/{h.total_questions} · {pct}%</span>
            ) : (
              <span className="badge">Incomplete</span>
            )}
          </div>
        );
      })}
    </div>
  );
};
