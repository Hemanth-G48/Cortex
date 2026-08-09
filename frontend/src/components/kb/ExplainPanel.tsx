import { useState } from 'react';
import { endpoints, type KbExplainResponse } from '../../services/api';

interface Props {
  documentId: number;
}

const DEPTHS = [
  { key: 'overview', label: 'Overview' },
  { key: 'deep_dive', label: 'Deep dive' },
  { key: 'eli5', label: 'ELI5' },
  { key: 'analogy', label: 'Analogy' },
  { key: 'derivation', label: 'Derivation' },
] as const;

const styles = {
  card: {
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    background: 'var(--bg-card)',
    padding: '0.85rem 1rem',
    marginTop: '0.75rem',
  },
  title: { fontSize: '0.85rem', fontWeight: 700, margin: '0 0 0.5rem' },
  chips: { display: 'flex', gap: '0.3rem', flexWrap: 'wrap' as const, marginBottom: '0.5rem' },
  chip: {
    fontSize: '0.68rem', fontWeight: 600, padding: '0.2rem 0.6rem', borderRadius: 999,
    border: '1px solid var(--border)', background: 'transparent', color: 'var(--text-secondary)',
    cursor: 'pointer', transition: 'all 0.15s',
  },
  chipActive: {
    background: 'var(--accent-muted)', borderColor: 'var(--accent)', color: 'var(--accent)',
  },
  body: { fontSize: '0.8rem', lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' as const },
  cite: {
    color: 'var(--accent)', cursor: 'pointer', fontWeight: 600, textDecoration: 'underline dotted',
  },
  fallback: {
    fontSize: '0.68rem', color: 'var(--warning)', marginTop: '0.4rem',
  },
};

export const ExplainPanel = ({ documentId }: Props) => {
  const [concept, setConcept] = useState('');
  const [depth, setDepth] = useState<(typeof DEPTHS)[number]['key']>('overview');
  const [data, setData] = useState<KbExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scrollTo, setScrollTo] = useState<number | null>(null);

  const run = async () => {
    const c = concept.trim();
    if (!c) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      setData(await endpoints.kb.explain.run({ concept: c, depth, document_ids: [documentId] }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const openCitation = async (chunkId: number) => {
    try {
      const chunks = await endpoints.kb.documents.chunks(documentId);
      const chunk = chunks.find((ch) => ch.id === chunkId);
      if (chunk) {
        setScrollTo(chunk.char_start);
        document.getElementById(`kb-chunk-${documentId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch {
      /* citation link only */
    }
  };

  return (
    <div className="card" style={styles.card}>
      <h4 style={styles.title}>💬 Explain a concept</h4>
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
        <input
          className="form-input"
          style={{ flex: 1, fontSize: '0.78rem' }}
          placeholder="e.g. entropy, photosynthesis…"
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void run()}
        />
        <button type="button" className="btn btn-sm btn-primary" disabled={loading || !concept.trim()} onClick={() => void run()}>
          {loading ? 'Explaining…' : 'Explain'}
        </button>
      </div>

      <div style={styles.chips}>
        {DEPTHS.map((d) => (
          <button
            key={d.key}
            type="button"
            style={{ ...styles.chip, ...(depth === d.key ? styles.chipActive : {}) }}
            onClick={() => setDepth(d.key)}
          >
            {d.label}
          </button>
        ))}
      </div>

      {error && <p style={{ fontSize: '0.75rem', color: 'var(--danger)' }}>{error}</p>}
      {scrollTo !== null && (
        <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>↳ scrolled to section at char {scrollTo}</p>
      )}

      {data && (
        <div className="fade-in">
          <p style={styles.body}>{data.explanation}</p>
          {data.citations.length > 0 && (
            <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
              {data.citations.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  title={`${c.title ?? ''} — ${c.heading_path ?? ''}`}
                  style={styles.cite}
                  onClick={() => void openCitation(c.chunk_id)}
                >
                  [{i + 1}] {c.title}
                </button>
              ))}
            </div>
          )}
          {data.fallback && (
            <div style={styles.fallback}>⚡ Deterministic fallback — no AI call was made.</div>
          )}
        </div>
      )}
    </div>
  );
};
