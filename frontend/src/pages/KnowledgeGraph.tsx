import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import {
  endpoints,
  type KbGraphNode,
  type KbGraphResponse,
  type KbSource,
} from '../services/api';
import ForceGraph from 'react-force-graph-2d';

const KIND_COLORS: Record<string, string> = {
  document: '#3b82f6',
  concept: '#10b981',
  tag: '#f59e0b',
};

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
    (node: KbGraphNode) => {
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

  // Build ForceGraph-compatible data
  const fgNodes = graphData?.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    kind: n.kind,
    doc_type: n.doc_type ?? null,
    status: n.status ?? null,
    degree: n.degree,
    color: KIND_COLORS[n.kind] ?? '#6b7280',
  })) ?? [];

  const fgLinks = (graphData?.edges ?? []).map((e) => ({
    source: e.source,
    target: e.target,
    relation: e.relation,
    weight: e.weight,
    provenance: e.provenance,
  }));

  const nodeIdSet = new Set(fgNodes.map((n) => n.id));
  const filteredLinks = fgLinks.filter((l) => nodeIdSet.has(l.source as string) && nodeIdSet.has(l.target as string));

  const relationCounts = new Map<string, number>();
  (graphData?.edges ?? []).forEach((e) => {
    relationCounts.set(e.relation, (relationCounts.get(e.relation) ?? 0) + 1);
  });

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
        <div style={{ borderRadius: '8px', overflow: 'hidden', background: 'var(--bg-card, #181a1c)', border: '1px solid var(--border, #2d2d2d)', height: 600 }}>
          <ForceGraph
            graphData={{ nodes: fgNodes, links: filteredLinks }}
            nodeLabel="label"
            nodeColor="color"
            nodeRelSize={6}
            linkColor="rgba(75, 85, 99, 0.4)"
            linkWidth={(d: { weight: number }) => Math.max(0.5, (d as { weight: number }).weight * 2)}
            onNodeClick={(node: { id: string; kind: string } | null) => {
              if (node) handleNodeClick(node as unknown as KbGraphNode);
            }}
            enableNodeDrag={false}
            cooldownTicks={200}
          />
          {/* Legend overlay */}
          <div
            style={{
              position: 'absolute',
              bottom: '0.5rem',
              left: '0.5rem',
              display: 'flex',
              gap: '0.75rem',
              fontSize: '0.7rem',
              color: 'var(--text-secondary)',
              background: 'var(--bg-card, #181a1c)',
              padding: '0.3rem 0.6rem',
              borderRadius: '6px',
              border: '1px solid var(--border, #2d2d2d)',
              pointerEvents: 'none',
            }}
          >
            {Object.entries(KIND_COLORS).map(([kind, color]) => (
              <span key={kind} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
                {kind}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Load more ── */}
      {graphData?.truncated && !expanded && (
        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <button type="button" className="btn btn-ghost" onClick={() => handleLoadMore()}>
            Load more ({graphData.total_nodes} nodes, {graphData.total_edges} edges)
          </button>
        </div>
      )}

      {graphData && !graphData.truncated && fgNodes.length > 0 && (
        <p style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
          {graphData.total_nodes} nodes · {graphData.total_edges} edges
        </p>
      )}
    </div>
  );
};
