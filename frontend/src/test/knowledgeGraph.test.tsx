import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { KnowledgeGraph } from '../pages/KnowledgeGraph';
import { endpoints } from '../services/api';

const renderGraph = () =>
  render(
    <MemoryRouter>
      <KnowledgeGraph />
    </MemoryRouter>,
  );

// Sigma draws to <canvas> (jsdom cannot) and the force supervisor spawns a Web
// Worker (jsdom has none). Stub both so these tests exercise the page logic
// (data fetching, filters, empty states) rather than rendering internals.
vi.mock('sigma', () => ({
  default: class MockSigma {
    on() {
      return this;
    }
    kill() {}
    refresh() {}
    getCamera() {
      return { ratio: 1, animatedZoom: vi.fn(), animatedUnzoom: vi.fn(), animate: vi.fn() };
    }
    getBBox() {
      return { x: [0, 1], y: [0, 1] };
    }
    getContainer() {
      return { clientWidth: 600, clientHeight: 600 };
    }
    getGraphToViewportRatio() {
      return 1;
    }
  },
}));

vi.mock('sigma/rendering', () => ({
  NodeProgram: class MockNodeProgram {
    constructor(..._args: unknown[]) {}
  },
}));

vi.mock('sigma/utils', () => ({
  floatColor: () => 0,
}));

vi.mock('graphology-layout-force/worker', () => ({
  default: class MockForceSupervisor {
    start() {}
    stop() {}
    kill() {}
    isRunning() {
      return false;
    }
  },
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
    { id: 1, user_id: 1, name: 'Obsidian Vault', source_type: 'vault_folder' as const, root_path: '/home/me/vault', enabled: true, last_scanned_at: '2026-08-05T10:00:00', files_seen: 4, files_added: 2, files_changed: 1, files_removed: 0, total_files: 4, status: 'ready' as const, error: null, created_at: '2026-08-05T10:00:00', updated_at: '2026-08-05T10:00:00' },
    { id: 2, user_id: 1, name: 'Local Notes', source_type: 'local_dir' as const, root_path: '/home/me/notes', enabled: true, last_scanned_at: null, files_seen: 0, files_added: 0, files_changed: 0, files_removed: 0, total_files: 0, status: 'ready' as const, error: null, created_at: '2026-08-05T10:00:00', updated_at: '2026-08-05T10:00:00' },
  ];

  return {
    endpoints: {
      kb: {
        graph: {
          list: vi.fn(async () => ({ nodes, edges, truncated: false, total_nodes: nodes.length, total_edges: edges.length })),
          get: vi.fn(),
          stats: vi.fn(),
          saveLayout: vi.fn(),
          loadLayout: vi.fn(),
        },
        sources: {
          list: vi.fn(async () => ({ items: sources, total: 2 })),
        },
      },
    },
  };
});

describe('Knowledge Graph page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders graph when data is returned', async () => {
    renderGraph();
    await waitFor(() => expect(screen.getByTestId('force-graph')).toBeInTheDocument());
    expect(screen.getByTestId('force-graph')).toHaveAttribute('data-nodes', '4');
  });

  it('shows empty state when no data', async () => {
    vi.mocked(endpoints.kb.graph.list).mockResolvedValueOnce({
      nodes: [],
      edges: [],
      truncated: false,
      total_nodes: 0,
      total_edges: 0,
    });
    renderGraph();
    await waitFor(() => expect(screen.getByText('No graph data yet')).toBeInTheDocument());
  });
});
