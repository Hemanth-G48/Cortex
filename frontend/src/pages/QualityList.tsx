import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { endpoints, type KbQualityItem } from '../services/api';

const scoreColor = (score: number) =>
  score >= 75 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--danger)';

const fmtPct = (n: number | undefined) => (n === undefined ? 0 : Math.round(n * 100));

export const QualityList = () => {
  const [items, setItems] = useState<KbQualityItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await endpoints.kb.quality.list();
      setItems(res.items);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="page-section">
      <Header title="Note Quality Work-List" />

      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Every vault note scored 0–100 (length · headings · links · recency · concept coverage). Lowest scores first — a great place to find notes worth improving.
      </p>

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Scoring notes…</p>
      ) : items.length === 0 ? (
        <EmptyState icon="🏆" title="No notes yet" message="Scan a source or upload documents to start scoring note quality." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {items.map((d) => (
            <Link
              key={d.document_id}
              to={`/knowledge-base?doc=${d.document_id}`}
              className="card"
              style={{
                display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem',
                textDecoration: 'none', color: 'inherit', flexWrap: 'wrap',
              }}
            >
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: scoreColor(d.score), width: 56, textAlign: 'center' }}>
                {d.score}
              </div>
              <div style={{ flex: 1, minWidth: 180 }}>
                <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{d.title}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  {d.doc_type.toUpperCase()}
                  {d.suggestions > 0 ? ` · 💡 ${d.suggestions} suggestion${d.suggestions === 1 ? '' : 's'}` : ''}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.7rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                <span>📏 {fmtPct(d.components?.length)}%</span>
                <span>#️⃣ {fmtPct(d.components?.headings)}%</span>
                <span>🔗 {fmtPct(d.components?.links)}%</span>
                <span>🕒 {fmtPct(d.components?.recency)}%</span>
                <span>💡 {fmtPct(d.components?.coverage)}%</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
