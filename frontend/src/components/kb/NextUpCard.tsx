import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { endpoints, type KbRecommendItem } from '../../services/api';

const REASON_LABELS: Record<string, string> = {
  readiness: 'prerequisites ready',
  weakness: 'weakest topic',
  due_reviews: 'due for review',
  concept_gaps: 'concept gap',
  exam_proximity: 'exam soon',
  subject_coverage: 'subject behind',
};

/**
 * Phase 8 (Idea 75) — "what to study next": the single best cross-subject
 * action with an explainable reason breakdown, rendered as a dashboard card.
 */
export const NextUpCard = () => {
  const navigate = useNavigate();
  const [item, setItem] = useState<KbRecommendItem | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    endpoints.kb.recommend
      .next(1)
      .then((r) => setItem(r.items[0] ?? null))
      .catch(() => setItem(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Finding your next study action…</div>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="card" style={{ padding: '1rem' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.25rem' }}>🎯 Next up</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          No recommendations yet — import a syllabus or add topics to get a personalized next action.
        </div>
      </div>
    );
  }

  const reasons = Object.entries(item.reasons)
    .filter(([, v]) => (v as number) > 0)
    .sort((a, b) => (b[1] as number) - (a[1] as number));

  return (
    <div className="card" style={{ padding: '1rem', borderLeft: '3px solid var(--accent)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '1.1rem' }}>🎯</span>
        <span style={{ fontSize: '0.8rem', fontWeight: 800, letterSpacing: '0.03em', textTransform: 'uppercase' }}>
          Next up
        </span>
        <span style={{ flex: 1 }} />
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void load()} title="Refresh">
          ↻
        </button>
      </div>

      <div style={{ fontSize: '1rem', fontWeight: 700 }}>{item.topic_name}</div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '0.2rem 0 0.5rem' }}>
        {item.ready ? 'Ready to study' : 'Blocked by a prerequisite'} · {item.session_length_mins} min session
      </div>

      {reasons.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginBottom: '0.75rem' }}>
          {reasons.map(([k]) => (
            <span
              key={k}
              style={{
                fontSize: '0.66rem', padding: '0.15rem 0.5rem', borderRadius: 999,
                background: 'var(--accent)1a', color: 'var(--accent)', fontWeight: 600,
              }}
            >
              {REASON_LABELS[k] ?? k}
            </span>
          ))}
        </div>
      )}

      <button
        type="button"
        className="btn btn-primary btn-sm"
        onClick={() => navigate(`/practice?topic=${item.topic_id}`)}
      >
        ▶ Start studying
      </button>
    </div>
  );
};
