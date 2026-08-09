import { useEffect, useState } from 'react';
import { downloadAsFile, endpoints, type KbMindMapNode } from '../../services/api';

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
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: '0.5rem', marginBottom: '0.5rem',
  },
  title: { fontSize: '0.85rem', fontWeight: 700, margin: 0 },
  tree: { fontFamily: 'inherit', fontSize: '0.78rem' },
  row: {
    display: 'flex', alignItems: 'center', gap: '0.35rem',
    padding: '0.18rem 0.35rem', borderRadius: 6, cursor: 'pointer',
    transition: 'background 0.12s',
  },
  toggle: {
    width: 18, height: 18, borderRadius: 5, border: '1px solid var(--border)',
    background: 'var(--bg-hover)', color: 'var(--text-secondary)', fontSize: '0.6rem',
    lineHeight: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, cursor: 'pointer',
  },
  concept: {
    fontSize: '0.62rem', background: 'var(--success-muted)', color: 'var(--success)',
    padding: '0.05rem 0.45rem', borderRadius: 999, marginLeft: '0.25rem',
  },
  levelLine: { borderLeft: '1px solid var(--border)', marginLeft: 9, paddingLeft: 8 },
};

function TreeNode({ node, depth }: { node: KbMindMapNode; depth: number }) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = node.children.length > 0;

  return (
    <div>
      <div style={{ ...styles.row, paddingLeft: depth > 0 ? 0 : '0.35rem' }}>
        {hasChildren && (
          <button type="button" style={styles.toggle} onClick={() => setOpen((o) => !o)}>
            {open ? '−' : '+'}
          </button>
        )}
        <span
          style={{
            fontWeight: depth === 0 ? 700 : 500,
            color: depth === 0 ? 'var(--accent)' : 'var(--text-primary)',
          }}
        >
          {node.label}
        </span>
        {node.concepts.map((c) => (
          <span key={c} style={styles.concept}>💡 {c}</span>
        ))}
      </div>
      {open && hasChildren && (
        <div style={styles.levelLine}>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export const MindMapView = ({ documentId }: Props) => {
  const [tree, setTree] = useState<KbMindMapNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    endpoints.kb.mindmap
      .get(documentId)
      .then(setTree)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [documentId]);

  const exportMap = async (format: 'markdown' | 'opml') => {
    setExporting(format);
    try {
      await downloadAsFile(
        endpoints.kb.mindmap.exportUrl(documentId, format),
        format === 'markdown' ? `mindmap-${documentId}.md` : `mindmap-${documentId}.opml`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="card" style={styles.card}>
      <div style={styles.header}>
        <h4 style={styles.title}>🗺️ Mind map</h4>
        {tree && (
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            <button type="button" className="btn btn-sm btn-ghost" disabled={exporting !== null} onClick={() => void exportMap('markdown')}>
              {exporting === 'markdown' ? '…' : 'Markdown'}
            </button>
            <button type="button" className="btn btn-sm btn-ghost" disabled={exporting !== null} onClick={() => void exportMap('opml')}>
              {exporting === 'opml' ? '…' : 'OPML'}
            </button>
          </div>
        )}
      </div>
      {loading ? (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Building tree…</p>
      ) : error ? (
        <p style={{ fontSize: '0.75rem', color: 'var(--danger)' }}>{error}</p>
      ) : tree ? (
        <div style={{ maxHeight: 260, overflowY: 'auto', ...styles.tree } as React.CSSProperties}>
          <TreeNode node={tree} depth={0} />
          {tree.children.length === 0 && (
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
              No headings detected — this document is flat.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
};
