import { useState } from 'react';

interface SummaryProps {
  title?: string;
  content: string;
  keyPoints?: string[];
  cached?: boolean;
}

/** Collapsible summary viewer: key points + content body (plan Phase 65). */
export const Summary = ({ title = 'Summary', content, keyPoints = [], cached }: SummaryProps) => {
  const [open, setOpen] = useState(true);

  return (
    <div className="card" style={{ borderColor: cached ? 'var(--info)' : 'var(--success)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '1.1rem' }} aria-hidden>✨</span>
          <strong style={{ fontSize: '0.9rem' }}>{title}</strong>
          {cached && <span className="badge badge-info">cached</span>}
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {open && (
        <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.75rem' }}>
          {keyPoints.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: '1.1rem', display: 'grid', gap: '0.35rem' }}>
              {keyPoints.map((k, i) => (
                <li key={i} style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>{k}</li>
              ))}
            </ul>
          )}
          {content && (
            <div
              style={{
                fontSize: '0.85rem',
                lineHeight: 1.65,
                color: 'var(--text-secondary)',
                whiteSpace: 'pre-wrap',
                borderTop: '1px solid var(--border)',
                paddingTop: '0.75rem',
                maxHeight: 320,
                overflowY: 'auto',
              }}
            >
              {content}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
