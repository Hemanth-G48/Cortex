import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KnowledgeGraphCanvas } from '../components/kb/KnowledgeGraphCanvas';
import type { KnowledgeGraphCanvasEdge, KnowledgeGraphCanvasNode } from '../components/kb/KnowledgeGraphCanvas';

// sigma draws to <canvas> (jsdom cannot) and the force supervisor spawns a Web
// Worker (jsdom has none). Stub those — but NOT graphology, so this test runs
// the real `new Graph()` + `graph.addEdge` code path that regressed.
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
      return { clientWidth: 600, clientHeight: 600, getBoundingClientRect: () => ({ width: 600, height: 600 }) };
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

const nodes: KnowledgeGraphCanvasNode[] = [
  { id: 'doc:1', label: 'Processes', kind: 'document', doc_type: 'md', status: 'unchanged', degree: 3, color: '#3b82f6' },
  { id: 'doc:2', label: 'Threads', kind: 'document', doc_type: 'md', status: 'unchanged', degree: 2, color: '#3b82f6' },
  { id: 'concept:1', label: 'scheduling', kind: 'concept', doc_type: null, status: null, degree: 1, color: '#10b981' },
];

// The backend's build_graph legitimately emits parallel edges between the same
// pair with different relations (WIKILINK + BACKLINK + SHARES_CONCEPT…).
const parallelEdges: KnowledgeGraphCanvasEdge[] = [
  { source: 'doc:1', target: 'doc:2', relation: 'WIKILINK', weight: 1, provenance: 'rule' },
  { source: 'doc:2', target: 'doc:1', relation: 'BACKLINK', weight: 1, provenance: 'rule' },
  { source: 'doc:1', target: 'doc:2', relation: 'SHARES_CONCEPT', weight: 0.4, provenance: 'rule' },
  { source: 'doc:1', target: 'concept:1', relation: 'MENTIONS', weight: 0.8, provenance: 'rule' },
];

describe('KnowledgeGraphCanvas (parallel-edge regression)', () => {
  it('renders without crashing when the same node pair has multiple edges', () => {
    // Regression: graphology's default single graph throws on the second edge
    // ("an edge linking doc:1 to doc:2 already exists"), which crashed the
    // whole Subject Details page. The canvas must use a multi-graph.
    render(<KnowledgeGraphCanvas nodes={nodes} edges={parallelEdges} height={300} />);
    expect(screen.getByTestId('force-graph')).toHaveAttribute('data-nodes', '3');
    expect(screen.getByTestId('sigma-container')).toBeInTheDocument();
  });

  it('dedupes exact (source, target, relation) triples', () => {
    const dupEdges: KnowledgeGraphCanvasEdge[] = [
      ...parallelEdges,
      // Exact duplicate of an existing edge — must be ignored, not re-added.
      { source: 'doc:1', target: 'doc:2', relation: 'WIKILINK', weight: 1, provenance: 'rule' },
    ];
    render(<KnowledgeGraphCanvas nodes={nodes} edges={dupEdges} height={300} />);
    expect(screen.getByTestId('force-graph')).toHaveAttribute('data-nodes', '3');
  });

  it('renders the empty state for no nodes', () => {
    render(<KnowledgeGraphCanvas nodes={[]} edges={[]} height={300} />);
    expect(screen.getByText(/No graph data for this subject/)).toBeInTheDocument();
  });
});
