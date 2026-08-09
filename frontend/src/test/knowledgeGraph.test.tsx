import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { KnowledgeGraph } from '../pages/KnowledgeGraph';

const renderGraph = () =>
  render(
    <MemoryRouter>
      <KnowledgeGraph />
    </MemoryRouter>,
  );

// react-force-graph-2d renders to <canvas>, which jsdom cannot do. Stub it so
// these tests exercise the page logic (data fetching, filters, empty states)
// rather than canvas drawing.
vi.mock('react-force-graph-2d', () => ({
  default: (props: { graphData?: { nodes?: unknown[]; links?: unknown[] } }) => (
    <div data-testid="force-graph" data-nodes={props.graphData?.nodes?.length ?? 0} />
  ),
}));

vi.mock('../services/api', () => {
  const nodes = [
    { id: 'doc:1', kind: 'document' as const, label: 'hello.md', doc_type: 'md', status: 'unchanged', degree: 3 },
    { id: 'doc:2', kind: 'document' as const, label: 'notes.md', doc_type: 'md', status: 'new', degree: 1 },
    { id: 'concept:1', kind: 'concept' as const, label: 'wikilink', degree: 2 },
    { id: 'tag:1', kind: 'tag' as const, label: 'math', degree: 2 },
  ];
  const edges = [
    { source: 'doc:1', target: 'doc:2', relation: 'WIKILINK', weight: 1, provenance: 'auto' },
    { source: 'doc:1', target: 'concept:1', relation: 'MENTIONS', weight: 0.8, provenance: 'auto' },
    { source: 'concept:1', target: 'tag:1', relation: 'RELATED', weight: 0.5, provenance: 'auto' },
  ];

  const sources = [
    { id: 1, user_id: 1, name: 'Obsidian Vault', source_type: 'vault_folder' as const, root_path: '/home/me/vault', enabled: true, last_scanned_at: '2026-08-05T10:00:00', files_seen: 4, files_added: 2, files_changed: 1, files_removed: 0, created_at: '2026-08-01T00:00:00', document_count: 3 },
  ];

  return {
    endpoints: {
      login: vi.fn().mockResolvedValue({ user: null }),
      kb: {
        sources: {
          list: vi.fn().mockResolvedValue({ items: sources, total: 1 }),
          get: vi.fn(),
          create: vi.fn(),
          update: vi.fn(),
          remove: vi.fn(),
          scan: vi.fn(),
        },
        documents: {
          list: vi.fn(),
          get: vi.fn(),
          remove: vi.fn(),
          upload: vi.fn(),
          chunks: vi.fn(),
          versions: vi.fn(),
          restore: vi.fn(),
          diff: vi.fn(),
          reindex: vi.fn(),
        },
        papers: { import: vi.fn() },
        jobs: { list: vi.fn(), get: vi.fn() },
        graph: {
          list: vi.fn().mockResolvedValue({ nodes, edges, truncated: false, total_nodes: 4, total_edges: 3 }),
        },
      },
    },
  };
});

describe('Knowledge Graph page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders graph data into the force graph and shows relation counts', async () => {
    renderGraph();
    // The canvas is stubbed — assert the stub received the mocked nodes.
    await waitFor(() => expect(screen.getByTestId('force-graph')).toBeInTheDocument());
    expect(screen.getByTestId('force-graph')).toHaveAttribute('data-nodes', '4');
    // Edge counts surface in the relation filter buttons.
    await waitFor(() => expect(screen.getByRole('button', { name: /WIKILINK.*1/ })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /MENTIONS.*1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /RELATED.*1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'BACKLINK' })).toBeInTheDocument();
  });

  it('renders filter controls and relation buttons', async () => {
    renderGraph();
    await waitFor(() => expect(screen.getByRole('button', { name: /WIKILINK/ })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /BACKLINK/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /MENTIONS/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /RELATED/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /SHARES_CONCEPT/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /DUPLICATE_OF/ })).toBeInTheDocument();
    // The sources select's accessible name comes from its options.
    expect(screen.getByRole('option', { name: 'All sources' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Search concepts \/ tags…/)).toBeInTheDocument();
  });

  it('re-fetches graph when a relation filter is clicked', async () => {
    const { endpoints } = await import('../services/api');
    renderGraph();
    const wikilinkBtn = await screen.findByRole('button', { name: /WIKILINK/ });
    wikilinkBtn.click();
    await waitFor(() =>
      expect(endpoints.kb.graph.list).toHaveBeenCalledWith(
        expect.objectContaining({ relation: 'WIKILINK' }),
      ),
    );
  });

  it('renders empty state when no nodes', async () => {
    const { endpoints } = await import('../services/api');
    // The vi.mock factory return is not typed as a mock; cast for the call.
    const listMock = endpoints.kb.graph.list as unknown as ReturnType<typeof vi.fn>;
    listMock.mockResolvedValueOnce({ nodes: [], edges: [], truncated: false, total_nodes: 0, total_edges: 0 });
    renderGraph();
    await waitFor(() => expect(screen.getByText(/No graph data yet/)).toBeInTheDocument());
    expect(screen.getByText(/Ingest documents/)).toBeInTheDocument();
  });

  it('renders loading state initially', () => {
    renderGraph();
    expect(screen.getByText(/Loading graph…/)).toBeInTheDocument();
  });
});
