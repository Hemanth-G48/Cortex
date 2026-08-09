import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { CitationResultCard } from '../components/kb/CitationResultCard';
import { endpoints, type KbSearchItem, type KbSearchMode } from '../services/api';

const MODES: { value: KbSearchMode; label: string }[] = [
  { value: 'keyword', label: 'Keyword' },
  { value: 'semantic', label: 'Semantic' },
  { value: 'hybrid', label: 'Hybrid' },
];

const PAGE_SIZE = 10;

export const VaultSearch = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const urlQuery = params.get('q') ?? '';
  const urlMode = (params.get('mode') as KbSearchMode | null) ?? 'hybrid';

  const [query, setQuery] = useState(urlQuery);
  const [mode, setMode] = useState<KbSearchMode>(urlMode);
  const [page, setPage] = useState(1);

  const [items, setItems] = useState<KbSearchItem[]>([]);
  const [total, setTotal] = useState(0);
  const [expandedQuery, setExpandedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Deep-linkable: ?q=...&mode=...&page=... (phrase 50)
  const runSearch = useCallback(
    async (q: string, m: KbSearchMode, p: number) => {
      const trimmed = q.trim();
      if (!trimmed) {
        setItems([]);
        setTotal(0);
        setExpandedQuery('');
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await endpoints.kb.search.run(trimmed, { mode: m, page: p, page_size: PAGE_SIZE });
        setItems(res.items);
        setTotal(res.total);
        setExpandedQuery(res.expanded_query !== res.original_query ? res.expanded_query : '');
      } catch (e) {
        setError((e as Error).message);
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Keep URL in sync so results stay deep-linkable.
  useEffect(() => {
    const next = new URLSearchParams();
    if (query.trim()) next.set('q', query.trim());
    next.set('mode', mode);
    if (page > 1) next.set('page', String(page));
    const qs = next.toString();
    setParams(qs ? `?${qs}` : '', { replace: true });
  }, [query, mode, page, setParams]);

  // Debounced auto-search (reuse the MaterialSearch 300ms pattern) so typing
  // doesn't hammer the API; Enter/submit searches immediately via submit().
  useEffect(() => {
    if (!query.trim()) {
      setItems([]);
      setTotal(0);
      setExpandedQuery('');
      return;
    }
    const t = window.setTimeout(() => {
      void runSearch(query, mode, page);
    }, 300);
    return () => window.clearTimeout(t);
  }, [runSearch, query, mode, page]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    setPage(1);
    void runSearch(query, mode, 1);
  };

  const openItem = (item: KbSearchItem) => {
    // Click-through tracking (Idea 25 phrase 48 / Idea 29) — best effort.
    void endpoints.kb.search.feedback({ query, mode, chunk_id: item.chunk_id, clicked: true }).catch(() => {});
    navigate(`/knowledge-base?doc=${item.document_id}`);
  };

  const rateItem = (item: KbSearchItem, rating: -1 | 0 | 1) => {
    void endpoints.kb.search.feedback({ query, mode, chunk_id: item.chunk_id, rating }).catch(() => {});
  };

  return (
    <div className="page-section">
      <Header title="Vault Search" />

      {/* ── Query box + mode toggle ── */}
      <form onSubmit={submit} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <input
          className="form-input"
          style={{ flex: 1, minWidth: 220 }}
          placeholder="Search your notes… (natural language works in Hybrid mode)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search query"
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : '🔎 Search'}
        </button>
      </form>

      <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Mode:</span>
        {MODES.map((m) => (
          <button
            key={m.value}
            type="button"
            className={`btn btn-sm ${mode === m.value ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => {
              setMode(m.value);
              setPage(1);
            }}
            aria-pressed={mode === m.value}
          >
            {m.label}
          </button>
        ))}
        {total > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            {total} result{total === 1 ? '' : 's'} · page {page}/{totalPages}
          </span>
        )}
      </div>

      {/* ── Expanded-query hint (phrase 40) ── */}
      {expandedQuery && (
        <div
          style={{
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            background: '#f59e0b1a',
            border: '1px solid #f59e0b40',
            borderRadius: 8,
            padding: '0.4rem 0.7rem',
            marginBottom: '0.75rem',
          }}
        >
          ⚡ expanded: <code>{expandedQuery}</code>
        </div>
      )}

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {/* ── Results ── */}
      {loading && !items.length ? (
        <p style={{ color: 'var(--text-secondary)', padding: '2rem' }}>Searching…</p>
      ) : !query.trim() ? (
        <EmptyState icon="🔎" title="Search your vault" message="Type a query and pick a mode. Hybrid combines keyword + semantic retrieval." />
      ) : items.length === 0 ? (
        <EmptyState icon="🕳️" title="No matches" message={`Nothing matched “${query}”. Try fewer words or switch modes.`} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
          {items.map((item) => (
            <CitationResultCard key={`${item.chunk_id}-${item.document_id}`} item={item} query={query} onOpen={openItem} onFeedback={rateItem} />
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {total > PAGE_SIZE && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', marginTop: '1rem' }}>
          <button type="button" className="btn btn-sm btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            ← Prev
          </button>
          <span style={{ fontSize: '0.75rem', alignSelf: 'center', color: 'var(--text-secondary)' }}>
            {page} / {totalPages}
          </span>
          <button type="button" className="btn btn-sm btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next →
          </button>
        </div>
      )}
    </div>
  );
};
