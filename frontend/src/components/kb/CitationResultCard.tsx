import { useMemo } from 'react';
import type { KbSearchItem } from '../../services/api';

const MARK_RE = /<mark>|<\/mark>/g;

interface Props {
  item: KbSearchItem;
  /** Original user query — used for click-through tracking + feedback. */
  query: string;
  /** Optional: fired when the card body is opened (click-through tracking). */
  onOpen?: (item: KbSearchItem) => void;
  onFeedback?: (item: KbSearchItem, rating: -1 | 0 | 1) => void;
}

/**
 * Render an FTS snippet, turning the backend's `<mark>`/`</mark>` marker tokens
 * into real <mark> elements. Every segment is rendered as a React text child
 * (auto-escaped) — no dangerouslySetInnerHTML, so snippets can't inject HTML.
 */
function HighlightedSnippet({ snippet }: { snippet: string }) {
  const parts = useMemo(() => {
    const out: { text: string; hit: boolean }[] = [];
    let hit = false;
    let last = 0;
    for (const m of snippet.matchAll(MARK_RE)) {
      const before = snippet.slice(last, m.index);
      if (before) out.push({ text: before, hit });
      hit = m[0] === '<mark>';
      last = (m.index ?? 0) + m[0].length;
    }
    const tail = snippet.slice(last);
    if (tail) out.push({ text: tail, hit });
    return out;
  }, [snippet]);

  if (parts.length === 0) return <>{snippet || '—'}</>;
  return (
    <>
      {parts.map((p, i) =>
        p.hit ? (
          <mark key={i} style={{ background: 'rgba(245, 158, 11, 0.35)', borderRadius: 3, padding: '0 0.1rem' }}>
            {p.text}
          </mark>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </>
  );
}

/** Estimate a PDF page from the chunk's character offset (~3k chars/page). */
function estimatePage(item: KbSearchItem): number | null {
  if (item.doc_type !== 'pdf' || item.char_start <= 0) return null;
  return Math.floor(item.char_start / 3000) + 1;
}

export const CitationResultCard = ({ item, query, onOpen, onFeedback }: Props) => {
  const page = estimatePage(item);
  const path = item.source_path || item.title || `doc ${item.document_id}`;
  const sources = item.sources?.length ? item.sources : [];

  const handleOpen = () => {
    onOpen?.(item);
  };

  return (
    <article
      className="card"
      style={{
        padding: '0.85rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.4rem',
        transition: 'border-color 0.15s ease, transform 0.15s ease',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--accent, #2563eb)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border, #2d2d2d)';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn btn-sm btn-ghost"
          onClick={handleOpen}
          title="Open document"
          style={{ flex: 1, textAlign: 'left', justifyContent: 'flex-start', padding: 0, minWidth: 180 }}
        >
          <strong style={{ fontSize: '0.88rem' }}>{item.title || path}</strong>
        </button>
        <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="chip" style={{ fontSize: '0.62rem', background: 'var(--accent, #2563eb)1a', color: 'var(--accent, #2563eb)', padding: '0.1rem 0.45rem', borderRadius: 999, textTransform: 'uppercase', fontWeight: 700 }}>
            {item.doc_type}
          </span>
          {sources.map((s) => (
            <span key={s} style={{ fontSize: '0.6rem', background: '#10b98122', color: '#047857', padding: '0.1rem 0.45rem', borderRadius: 999, textTransform: 'uppercase', fontWeight: 700 }}>
              {s}
            </span>
          ))}
          <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
            {Math.round(item.score * 100) / 100}
          </span>
        </div>
      </div>

      {/* Citation line: source path · heading · page */}
      <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '55%' }} title={path}>
          📄 {path}
        </span>
        {item.heading_path && <span>· {item.heading_path}</span>}
        {page !== null && <span>· p.{page}</span>}
        {item.doc_date && <span>· {item.doc_date}</span>}
      </div>

      {/* Highlighted snippet */}
      <p style={{ fontSize: '0.78rem', lineHeight: 1.5, margin: 0, color: 'var(--text, #111)' }}>
        <HighlightedSnippet snippet={item.snippet} />
      </p>

      {/* Actions: open + feedback */}
      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginTop: '0.15rem' }}>
        <button type="button" className="btn btn-sm btn-ghost" onClick={handleOpen}>
          Open in vault →
        </button>
        {onFeedback && (
          <div style={{ display: 'flex', gap: '0.15rem', marginLeft: 'auto' }} role="group" aria-label="Rate this result">
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              title="Helpful"
              aria-label="Helpful result"
              onClick={() => onFeedback(item, 1)}
            >
              👍
            </button>
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              title="Not helpful"
              aria-label="Not helpful result"
              onClick={() => onFeedback(item, -1)}
            >
              👎
            </button>
          </div>
        )}
        {query && (
          <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }} title={`Matched query: ${query}`}>
            ↖ {query}
          </span>
        )}
      </div>
    </article>
  );
};
