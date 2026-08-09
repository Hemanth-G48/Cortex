import { useEffect, useState } from 'react';
import { endpoints, type KbSummaryResponse } from '../../services/api';

interface Props {
  documentId: number;
}

const styles = {
  card: {
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    background: 'var(--bg-card)',
    padding: '0.85rem 1rem',
    marginTop: '0.75rem',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '0.5rem',
    marginBottom: '0.5rem',
  },
  title: { fontSize: '0.85rem', fontWeight: 700, margin: 0 },
  chip: {
    fontSize: '0.62rem', fontWeight: 700, textTransform: 'uppercase' as const,
    letterSpacing: '0.05em', padding: '0.15rem 0.5rem', borderRadius: 999,
    background: 'var(--success-muted)', color: 'var(--success)', whiteSpace: 'nowrap' as const,
  },
  body: { fontSize: '0.8rem', lineHeight: 1.55, color: 'var(--text-primary)' },
  sub: { fontSize: '0.72rem', color: 'var(--text-secondary)', margin: '0.5rem 0 0.25rem', fontWeight: 700 },
  list: { margin: 0, paddingLeft: '1.1rem', fontSize: '0.76rem', color: 'var(--text-secondary)' },
};

export const SummaryPanel = ({ documentId }: Props) => {
  const [data, setData] = useState<KbSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = (regenerate = false) => {
    setLoading(true);
    setError(null);
    const p = regenerate
      ? endpoints.kb.summaries.regenerate(documentId)
      : endpoints.kb.summaries.get(documentId);
    p.then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  return (
    <div className="card" style={styles.card}>
      <div style={styles.header}>
        <h4 style={styles.title}>✨ AI Summary</h4>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
          {data?.cached && <span style={styles.chip}>cached</span>}
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            disabled={busy || loading}
            onClick={() => {
              setBusy(true);
              load(true);
              window.setTimeout(() => setBusy(false), 1200);
            }}
          >
            {busy ? '…' : '⟳ Regenerate'}
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Generating summary…</p>
      ) : error ? (
        <p style={{ fontSize: '0.75rem', color: 'var(--danger)' }}>{error}</p>
      ) : data ? (
        <>
          <p style={styles.body}>{data.summary.content}</p>

          {data.summary.key_points.length > 0 && (
            <>
              <div style={styles.sub}>Key points</div>
              <ul style={styles.list}>
                {data.summary.key_points.map((k, i) => (
                  <li key={i}>{k}</li>
                ))}
              </ul>
            </>
          )}

          {data.summary.definitions.length > 0 && (
            <>
              <div style={styles.sub}>Definitions</div>
              <ul style={styles.list}>
                {data.summary.definitions.map((d, i) => (
                  <li key={i}>
                    <strong>{d.term}</strong> — {d.definition}
                  </li>
                ))}
              </ul>
            </>
          )}

          {data.summary.open_questions.length > 0 && (
            <>
              <div style={styles.sub}>Open questions</div>
              <ul style={styles.list}>
                {data.summary.open_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </>
          )}
        </>
      ) : null}
    </div>
  );
};
