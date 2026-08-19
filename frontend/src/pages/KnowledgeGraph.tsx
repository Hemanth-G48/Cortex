import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { ErrorBoundary } from '../components/shared/ErrorBoundary';
import { KnowledgeGraphCanvas } from '../components/kb/KnowledgeGraphCanvas';
import { KIND_COLORS } from '../components/kb/graphConstants';
import {
  endpoints,
  type KbGraphResponse,
  type KbSource,
} from '../services/api';

const RELATION_LABELS = ['WIKILINK', 'BACKLINK', 'MENTIONS', 'RELATED', 'SHARES_CONCEPT', 'DUPLICATE_OF'];

const INITIAL_LIMIT = 200;

export const KnowledgeGraph = () => {
  const navigate = useNavigate();
  const [graphData, setGraphData] = useState<KbGraphResponse | null>(null);
  const [sources, setSources] = useState<KbSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // filters
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [relationFilter, setRelationFilter] = useState<string>('');
  const [conceptTagSearch, setConceptTagSearch] = useState('');
  const [expanded, setExpanded] = useState(false);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number | undefined> = { limit: expanded ? 1000 : INITIAL_LIMIT };
      if (sourceFilter) params.source = sourceFilter;
      if (relationFilter) params.relation = relationFilter;
      if (conceptTagSearch) params.concept = conceptTagSearch;
      const data = await endpoints.kb.graph.list(params);
      setGraphData(data);
    } catch (e) {
      setError((e as Error).message);
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  }, [sourceFilter, relationFilter, conceptTagSearch, expanded]);

  const loadSources = useCallback(async () => {
    try {
      const res = await endpoints.kb.sources.list();
      setSources(res.items);
    } catch {
      setSources([]);
    }
  }, []);

  useEffect(() => {
    void loadGraph();
    void loadSources();
  }, [loadGraph, loadSources]);

  const handleNodeClick = useCallback(
    (node: { id: string }) => {
      if (node.id.startsWith('doc:')) {
        const docId = node.id.slice('doc:'.length);
        navigate(`/knowledge-base?doc=${docId}`);
      }
    },
    [navigate],
  );

  const toggleRelation = (rel: string) => {
    setRelationFilter((prev) => (prev === rel ? '' : rel));
  };

  const handleLoadMore = () => {
    setExpanded(true);
  };

  // Derived graph data, memoized so the canvas only re-renders on new data.
  const { fgNodes, filteredLinks } = useMemo(() => {
    if (!graphData) return { fgNodes: [], filteredLinks: [] };
    const nodes = (graphData.nodes ?? []).map((n) => ({
      id: n.id,
      label: n.label,
      kind: n.kind,
      doc_type: n.doc_type ?? null,
      status: n.status ?? null,
      degree: n.degree,
      color: KIND_COLORS[n.kind] ?? '#6b7280',
    }));
    const links = (graphData.edges ?? []).map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.relation,
      weight: e.weight,
      provenance: e.provenance,
    }));
    const nodeIdSet = new Set(nodes.map((n) => n.id));
    const validLinks = links.filter((l) => nodeIdSet.has(l.source) && nodeIdSet.has(l.target));
    return { fgNodes: nodes, filteredLinks: validLinks };
  }, [graphData]);

  const relationCounts = useMemo(() => {
    const counts = new Map<string, number>();
    (graphData?.edges ?? []).forEach((e) => {
      counts.set(e.relation, (counts.get(e.relation) ?? 0) + 1);
    });
    return counts;
  }, [graphData]);

  return (
    <div className="page-section">
      <Header title="Knowledge Graph Explorer" />

      {error && (
        <div
          style={{
            padding: '0.6rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            background: '#ef444422',
            color: '#ef4444',
            fontSize: '0.85rem',
          }}
        >
          {error}
        </div>
      )}

      {/* ── Filters ── */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
        <select
          className="form-input"
          style={{ maxWidth: 220 }}
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
        >
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.id} value={String(s.id)}>{s.name}</option>
          ))}
        </select>

        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
          {RELATION_LABELS.map((rel) => {
            const count = relationCounts.get(rel) ?? 0;
            const active = relationFilter === rel;
            return (
              <button
                key={rel}
                type="button"
                className={`btn btn-sm ${active ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => toggleRelation(rel)}
                style={{ fontSize: '0.68rem' }}
              >
                {rel}
                {count > 0 && <span style={{ marginLeft: '0.2rem', opacity: 0.7 }}>({count})</span>}
              </button>
            );
          })}
        </div>

        <input
          className="form-input"
          style={{ minWidth: 160, flex: 1 }}
          placeholder="Search concepts / tags…"
          value={conceptTagSearch}
          onChange={(e) => setConceptTagSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && void loadGraph()}
        />

        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void loadGraph()}>
          ↻ Refresh
        </button>
      </div>

      {/* ── Graph ── */}
      {loading ? (
        <p style={{ color: 'var(--text-secondary)', padding: '2rem' }}>Loading graph…</p>
      ) : !graphData ? (
        <EmptyState icon="🕸️" title="No graph data" message={error ?? 'Something went wrong.'} />
      ) : fgNodes.length === 0 ? (
        <EmptyState
          icon="🕸️"
          title="No graph data yet"
          message="Ingest documents to build your knowledge graph."
          action={<button type="button" className="btn btn-primary" onClick={() => navigate('/knowledge-base')}>Go to Second Brain</button>}
        />
      ) : (
        <ErrorBoundary
          resetKey={`${graphData?.total_nodes ?? 0}:${graphData?.total_edges ?? 0}:${sourceFilter}:${relationFilter}:${conceptTagSearch}:${expanded}`}
          fallback={(_error, reset) => (
            <div
              className="notice notice-warning"
              role="alert"
              style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}
            >
              <strong>The knowledge graph failed to render.</strong>{' '}
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  reset();
                  void loadGraph();
                }}
              >
                ↻ Retry
              </button>
            </div>
          )}
        >
          <KnowledgeGraphCanvas nodes={fgNodes} edges={filteredLinks} onNodeClick={handleNodeClick} />
        </ErrorBoundary>
      )}

      {/* ── Load more ── */}
      {graphData?.truncated && !expanded && (
        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <button type="button" className="btn btn-ghost" onClick={() => handleLoadMore()}>
            Load more ({graphData.total_nodes ?? 0} nodes, {graphData.total_edges ?? 0} edges)
          </button>
        </div>
      )}

      {graphData && !graphData.truncated && fgNodes.length > 0 && (
        <p style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          {graphData.total_nodes ?? 0} nodes · {graphData.total_edges ?? 0} edges
        </p>
      )}
    </div>
  );
};
