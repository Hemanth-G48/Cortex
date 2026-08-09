import { useEffect, useState } from 'react';
import { endpoints, type KbQualityResult } from '../../services/api';

interface Props {
  documentId: number;
}

const COMPONENT_LABELS: Record<string, string> = {
  length: 'Length',
  headings: 'Headings',
  links: 'Link density',
  recency: 'Recency',
  coverage: 'Concept coverage',
};

const scoreColor = (score: number) =>
  score >= 75 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--danger)';

const styles = {
  card: {
    border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)',
    background: 'var(--bg-card)', padding: '0.85rem 1rem', marginTop: '0.75rem',
  },
  header: { display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' },
  score: { fontSize: '1.6rem', fontWeight: 800, lineHeight: 1 },
  bar: {
    height: 6, borderRadius: 3, background: 'var(--bg-hover)', overflow: 'hidden', flex: 1,
  },
  row: { display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem', fontSize: '0.7rem' },
};

export const QualityPanel = ({ documentId }: Props) => {
  const [data, setData] = useState<KbQualityResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    endpoints.kb.quality
      .document(documentId)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [documentId]);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await endpoints.kb.quality.generateSuggestions(documentId);
      setData((prev) =>
        prev ? { ...prev, suggestions: [...(res.items ?? []), ...(prev.suggestions ?? [])] } : prev,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const dismiss = async (id: number) => {
    await endpoints.kb.quality.dismissSuggestion(id);
    setData((prev) => (prev ? { ...prev, suggestions: prev.suggestions.filter((s) => s.id !== id) } : prev));
  };

  return (
    <div className="card" style={styles.card}>
      <div style={styles.header}>
        <h4 style={{ fontSize: '0.85rem', fontWeight: 700, margin: 0, flex: 1 }}>🏆 Note quality</h4>
        {loading ? (
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>…</span>
        ) : data ? (
          <span style={{ ...styles.score, color: scoreColor(data.score) }}>{data.score}</span>
        ) : null}
      </div>

      {loading ? (
        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Scoring…</p>
      ) : error ? (
        <p style={{ fontSize: '0.72rem', color: 'var(--danger)' }}>{error}</p>
      ) : data ? (
        <>
          {Object.entries(data.components ?? {}).map(([key, value]) => (
            <div key={key} style={styles.row}>
              <span style={{ width: 110, color: 'var(--text-secondary)' }}>
                {COMPONENT_LABELS[key] ?? key}
              </span>
              <div style={styles.bar}>
                <div
                  style={{ height: '100%', width: `${Math.round((value ?? 0) * 100)}%`, background: scoreColor(data.score), transition: 'width 0.4s' }}
                />
              </div>
              <span style={{ width: 34, textAlign: 'right', color: 'var(--text-muted)' }}>
                {Math.round((value ?? 0) * 100)}%
              </span>
            </div>
          ))}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: '0.6rem 0 0.3rem' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, flex: 1 }}>💡 Suggestions ({data.suggestions?.length ?? 0})</span>
            <button type="button" className="btn btn-sm btn-ghost" disabled={busy} onClick={() => void generate()}>
              {busy ? 'Generating…' : '✨ Generate'}
            </button>
          </div>
          {(data.suggestions ?? []).length === 0 ? (
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              No suggestions yet — generate coaching ideas.
            </p>
          ) : (
            (data.suggestions ?? []).map((s) => (
              <div key={s.id} style={{ display: 'flex', gap: '0.4rem', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.68rem', background: 'var(--accent-muted)', color: 'var(--accent)', padding: '0.05rem 0.45rem', borderRadius: 999, whiteSpace: 'nowrap' }}>
                  {s.action}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', flex: 1 }}>{s.detail}</span>
                <button type="button" className="btn btn-sm btn-ghost" style={{ padding: 0, minWidth: 0, fontSize: '0.65rem' }} title="Dismiss" onClick={() => void dismiss(s.id)}>✕</button>
              </div>
            ))
          )}
        </>
      ) : null}
    </div>
  );
};
