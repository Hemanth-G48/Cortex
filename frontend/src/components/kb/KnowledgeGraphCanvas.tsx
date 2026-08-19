import { useCallback, useEffect, useRef, useState } from 'react';
import Graph from 'graphology';
import type { Attributes } from 'graphology-types';
import Sigma from 'sigma';
import ForceSupervisor from 'graphology-layout-force/worker';
import { NodeProgram } from 'sigma/rendering';
import type { ProgramInfo } from 'sigma/rendering';
import { floatColor } from 'sigma/utils';
import type { EdgeDisplayData, NodeDisplayData, RenderParams } from 'sigma/types';
import { EmptyState } from '../shared/EmptyState';
import { KIND_COLORS } from './graphConstants';

export interface KnowledgeGraphCanvasNode {
  id: string;
  label: string;
  kind: string;
  doc_type?: string | null;
  status?: string | null;
  degree: number;
  color: string;
}

export interface KnowledgeGraphCanvasEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  provenance: string;
}

export interface KnowledgeGraphCanvasClickNode {
  id: string;
  kind: string;
  label: string;
  degree: number;
  doc_type?: string | null;
  status?: string | null;
}

interface KnowledgeGraphCanvasProps {
  nodes: KnowledgeGraphCanvasNode[];
  edges: KnowledgeGraphCanvasEdge[];
  height?: number;
  onNodeClick?: (node: KnowledgeGraphCanvasClickNode) => void;
}

// Custom WebGL node program: renders nodes as glowing dots (bright core fading
// to transparent) instead of flat circles. WebGL enum values are hardcoded so
// this class never references `WebGLRenderingContext` at module scope — that
// global is absent in jsdom and would break imports.

const GLOW_UNIFORMS = ['u_sizeRatio', 'u_correctionRatio', 'u_matrix'] as const;

const GLOW_VERTEX_SHADER_SOURCE = `
  attribute vec4 a_id;
  attribute vec4 a_color;
  attribute vec2 a_position;
  attribute float a_size;
  attribute float a_angle;

  uniform mat3 u_matrix;
  uniform float u_sizeRatio;
  uniform float u_correctionRatio;

  varying vec4 v_color;
  varying vec2 v_diffVector;
  varying float v_radius;

  const float bias = 255.0 / 254.0;

  void main() {
    float size = a_size * u_correctionRatio / u_sizeRatio * 4.0;
    vec2 diffVector = size * vec2(cos(a_angle), sin(a_angle));
    vec2 position = a_position + diffVector;
    gl_Position = vec4((u_matrix * vec3(position, 1)).xy, 0, 1);

    v_diffVector = diffVector;
    v_radius = size / 2.0;

    #ifdef PICKING_MODE
    v_color = a_id;
    #else
    v_color = a_color;
    #endif

    v_color.a *= bias;
  }
`;

const GLOW_FRAGMENT_SHADER_SOURCE = `
  precision highp float;

  varying vec4 v_color;
  varying vec2 v_diffVector;
  varying float v_radius;

  const vec4 transparent = vec4(0.0, 0.0, 0.0, 0.0);

  void main(void) {
    float dist = length(v_diffVector) / v_radius;

    #ifdef PICKING_MODE
    // Solid hit area slightly larger than the core so hovering matches the glow.
    if (dist > 1.5)
      gl_FragColor = transparent;
    else
      gl_FragColor = v_color;
    #else
    // Soft radial gradient: bright core fading to a faint halo (Obsidian-like).
    float core = exp(-dist * dist * 7.0);
    float halo = exp(-dist * dist * 2.2);
    float alpha = v_color.a * (0.6 * core + 0.4 * halo);
    gl_FragColor = vec4(v_color.rgb, alpha);
    #endif
  }
`;

// WebGL constants (gl.TRIANGLES / gl.FLOAT / gl.UNSIGNED_BYTE).
const GL_TRIANGLES = 0x0004;
const GL_FLOAT = 0x1406;
const GL_UNSIGNED_BYTE = 0x1401;

class GlowNodeProgram extends NodeProgram<(typeof GLOW_UNIFORMS)[number]> {
  static readonly ANGLE_1 = 0;
  static readonly ANGLE_2 = (2 * Math.PI) / 3;
  static readonly ANGLE_3 = (4 * Math.PI) / 3;

  getDefinition() {
    return {
      VERTICES: 3,
      VERTEX_SHADER_SOURCE: GLOW_VERTEX_SHADER_SOURCE,
      FRAGMENT_SHADER_SOURCE: GLOW_FRAGMENT_SHADER_SOURCE,
      METHOD: GL_TRIANGLES,
      UNIFORMS: GLOW_UNIFORMS,
      ATTRIBUTES: [
        { name: 'a_position', size: 2, type: GL_FLOAT },
        { name: 'a_size', size: 1, type: GL_FLOAT },
        { name: 'a_color', size: 4, type: GL_UNSIGNED_BYTE, normalized: true },
        { name: 'a_id', size: 4, type: GL_UNSIGNED_BYTE, normalized: true },
      ],
      CONSTANT_ATTRIBUTES: [{ name: 'a_angle', size: 1, type: GL_FLOAT }],
      CONSTANT_DATA: [
        [GlowNodeProgram.ANGLE_1],
        [GlowNodeProgram.ANGLE_2],
        [GlowNodeProgram.ANGLE_3],
      ],
    };
  }

  processVisibleItem(nodeIndex: number, startIndex: number, data: NodeDisplayData): void {
    const array = this.array;
    const color = floatColor(data.color);
    array[startIndex++] = data.x;
    array[startIndex++] = data.y;
    array[startIndex++] = data.size;
    array[startIndex++] = color;
    array[startIndex++] = nodeIndex;
  }

  setUniforms(params: RenderParams, { gl, uniformLocations }: ProgramInfo): void {
    gl.uniform1f(uniformLocations.u_sizeRatio, params.sizeRatio);
    gl.uniform1f(uniformLocations.u_correctionRatio, params.correctionRatio);
    gl.uniformMatrix3fv(uniformLocations.u_matrix, false, params.matrix);
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function withAlpha(color: string, alpha: number): string {
  const hex = /^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/.exec(color);
  if (hex) {
    const [, r, g, b] = hex;
    return `rgba(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, ${alpha})`;
  }
  const shortHex = /^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$/.exec(color);
  if (shortHex) {
    const [, r, g, b] = shortHex;
    return `rgba(${parseInt(r + r, 16)}, ${parseInt(g + g, 16)}, ${parseInt(b + b, 16)}, ${alpha})`;
  }
  const rgba = /^rgba?\\(([^)]+)\\)$/i.exec(color);
  if (rgba) {
    const parts = rgba[1].split(',').map((p) => p.trim());
    return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha})`;
  }
  return color;
}

/**
 * Animate the camera so the graph bbox is visible with `padding` pixels of
 * margin. sigma v3 has no built-in `zoomToFit`; the target ratio is computed
 * from the live bbox and the current pixels-per-graph-unit.
 */
function fitGraph(renderer: Sigma, duration = 600, padding = 40): void {
  const camera = renderer.getCamera();
  const bbox = renderer.getBBox();
  const container = renderer.getContainer();
  const width = container.clientWidth || container.getBoundingClientRect().width || 600;
  const height = container.clientHeight || container.getBoundingClientRect().height || 600;
  const graphWidth = Math.max(bbox.x[1] - bbox.x[0], 1);
  const graphHeight = Math.max(bbox.y[1] - bbox.y[0], 1);
  const pxPerUnit = renderer.getGraphToViewportRatio();
  const targetRatio =
    camera.ratio *
    Math.min(
      (width - 2 * padding) / Math.max(graphWidth * pxPerUnit, 1),
      (height - 2 * padding) / Math.max(graphHeight * pxPerUnit, 1),
    );
  camera.animate(
    {
      x: (bbox.x[0] + bbox.x[1]) / 2,
      y: (bbox.y[0] + bbox.y[1]) / 2,
      ratio: targetRatio,
    },
    { duration },
    () => {},
  );
}

/**
 * Reusable sigma.js graph renderer (Obsidian-style glow nodes, force layout,
 * hover focus, local mode, zoom/fit controls). Used by the standalone
 * Knowledge Graph page and the Second Brain section of the Subject Details
 * page — both share the exact same rendering code path.
 */
export const KnowledgeGraphCanvas = ({ nodes, edges, height = 600, onNodeClick }: KnowledgeGraphCanvasProps) => {
  const [localMode, setLocalMode] = useState(false);
  // React state drives the local-mode hint; the ref mirrors it for the stable
  // reducers (hover changes call refresh() instead of rebuilding the renderer).
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<Sigma | null>(null);
  const layoutRef = useRef<ForceSupervisor | null>(null);
  const graphRef = useRef<Graph | null>(null);
  // Mutable values read by the stable reducers; hover changes call refresh()
  // instead of rebuilding the renderer.
  const hoveredNodeRef = useRef<string | null>(null);
  const localModeRef = useRef(false);
  const focusedNodesRef = useRef<Set<string>>(new Set());

  const toggleLocalMode = () => {
    const next = !localMode;
    localModeRef.current = next;
    setLocalMode(next);
    rendererRef.current?.refresh();
  };

  const handleZoomIn = () => {
    void rendererRef.current?.getCamera().animatedZoom({ duration: 200 });
  };

  const handleZoomOut = () => {
    void rendererRef.current?.getCamera().animatedUnzoom({ duration: 200 });
  };

  const handleFit = () => {
    if (rendererRef.current) fitGraph(rendererRef.current);
  };

  const handleEnterNode = useCallback((node: string) => {
    hoveredNodeRef.current = node;
    setHoveredNode(node);
    const graph = graphRef.current;
    focusedNodesRef.current = new Set(graph ? [node, ...graph.neighbors(node)] : [node]);
    rendererRef.current?.refresh();
  }, []);

  const handleLeaveNode = useCallback(() => {
    hoveredNodeRef.current = null;
    setHoveredNode(null);
    focusedNodesRef.current = new Set();
    rendererRef.current?.refresh();
  }, []);

  // ── Obsidian-style hover focus reducers ────────────────────────────────────
  // sigma reducers REPLACE the attribute object (they are not merged), so these
  // always return a full copy of `data` (raw attrs, typed Attributes so Sigma's
  // generic inference stays aligned with the graph's own node type).
  const nodeReducer = useCallback(
    (node: string, data: Attributes): Partial<NodeDisplayData> => {
      const hovered = hoveredNodeRef.current;
      if (!hovered) return data;
      if (node === hovered || focusedNodesRef.current.has(node)) return data;
      if (localModeRef.current) {
        return { ...data, hidden: true };
      }
      return { ...data, color: withAlpha(data.color, 0.15), size: (data.size ?? 4) * 0.6 };
    },
    [],
  );

  const edgeReducer = useCallback(
    (edge: string, data: Attributes): Partial<EdgeDisplayData> => {
      const hovered = hoveredNodeRef.current;
      const graph = graphRef.current;
      if (!hovered || !graph) return data;
      const source = graph.source(edge);
      const target = graph.target(edge);
      if (localModeRef.current) {
        if (focusedNodesRef.current.has(source) && focusedNodesRef.current.has(target)) return data;
        return { ...data, hidden: true };
      }
      if (source === hovered || target === hovered) return data;
      return { ...data, color: withAlpha(data.color, 0.08) };
    },
    [],
  );

  const nodeClickHandler = useCallback(
    (node: string) => {
      const graphInstance = graphRef.current;
      if (!graphInstance || !onNodeClick) return;
      const attrs = graphInstance.getNodeAttributes(node);
      onNodeClick({
        id: node,
        kind: attrs.kind,
        label: attrs.label,
        degree: attrs.degree,
        doc_type: attrs.doc_type,
        status: attrs.status,
      });
    },
    [onNodeClick],
  );

  // ── Build the graphology graph + sigma renderer ────────────────────────────
  useEffect(() => {
    if (nodes.length === 0) return;
    const container = containerRef.current;
    if (!container) return;

    // Multi-graph: the backend legitimately emits parallel edges between the
    // same document pair with different relations (WIKILINK + BACKLINK +
    // SHARES_CONCEPT, …). graphology's default single graph throws on the
    // second edge, which crashed the whole Subject Details page (and the
    // standalone Knowledge Graph page) — the uncaught error unmounted React's
    // tree. Parallel edges render as separate lines, which is correct.
    const graph = new Graph({ multi: true });
    const nodeCount = nodes.length;
    nodes.forEach((n, i) => {
      // Initial circular spread so the force layout starts from a stable ring.
      const angle = (i / nodeCount) * 2 * Math.PI;
      const radius = 90 + (i % 5) * 35;
      graph.addNode(n.id, {
        label: n.label,
        kind: n.kind,
        doc_type: n.doc_type,
        status: n.status,
        degree: n.degree,
        size: 3 + Math.min(n.degree, 10) * 0.5,
        color: n.color,
        x: radius * Math.cos(angle),
        y: radius * Math.sin(angle),
      });
    });
    // Defensive dedupe of exact (source, target, relation) triples — a true
    // duplicate with the same relation would still render as a double line.
    const seenEdges = new Set<string>();
    edges.forEach((l) => {
      if (l.source === l.target) return; // prune self-loops
      if (!graph.hasNode(l.source) || !graph.hasNode(l.target)) return;
      const key = `${l.source}|${l.target}|${l.relation}`;
      if (seenEdges.has(key)) return;
      seenEdges.add(key);
      graph.addEdge(l.source, l.target, {
        size: Math.max(0.3, l.weight * 1.2),
        color: 'rgba(255, 255, 255, 0.08)',
        relation: l.relation,
        weight: l.weight,
        type: 'line',
      });
    });

    graphRef.current = graph;

    const layout = new ForceSupervisor(graph, {
      settings: {
        attraction: 0.0005,
        repulsion: 4,
        gravity: 0.2,
        inertia: 0.6,
        maxMove: 200,
      },
    });
    layout.start();
    layoutRef.current = layout;

    const renderer = new Sigma(graph, container, {
      nodeProgramClasses: { glow: GlowNodeProgram },
      defaultNodeType: 'glow',
      nodeReducer,
      edgeReducer,
      labelDensity: 0.07,
      labelRenderedSizeThreshold: 14,
      renderLabels: true,
      minEdgeThickness: 0.3,
      defaultEdgeColor: 'rgba(255, 255, 255, 0.08)',
      defaultEdgeType: 'line',
      labelColor: { color: 'rgba(255, 255, 255, 0.8)' },
      allowInvalidContainer: true,
    });
    rendererRef.current = renderer;

    renderer.on('enterNode', ({ node }) => handleEnterNode(node));
    renderer.on('leaveNode', handleLeaveNode);
    renderer.on('clickNode', ({ node }) => nodeClickHandler(node));

    // Fit once the force layout has had a moment to settle.
    const fitTimer = window.setTimeout(() => {
      if (rendererRef.current) fitGraph(rendererRef.current);
    }, 1500);

    return () => {
      window.clearTimeout(fitTimer);
      layoutRef.current = null;
      layout.kill();
      rendererRef.current = null;
      renderer.kill();
      graphRef.current = null;
      hoveredNodeRef.current = null;
      focusedNodesRef.current = new Set();
    };
  }, [nodes, edges, nodeReducer, edgeReducer, handleEnterNode, handleLeaveNode, nodeClickHandler]);

  if (nodes.length === 0) {
    return (
      <EmptyState
        icon="🕸️"
        title="No graph data for this subject"
        message="Ingest documents tagged for this subject to build its knowledge graph."
      />
    );
  }

  return (
    <div
      data-testid="sigma-container"
      style={{
        position: 'relative',
        borderRadius: '8px',
        overflow: 'hidden',
        background: 'var(--bg-card, #1b1b1f)',
        border: '1px solid var(--border, #2d2d2d)',
        height,
      }}
    >
      <div
        ref={containerRef}
        data-testid="force-graph"
        data-nodes={nodes.length}
        style={{ position: 'absolute', inset: 0 }}
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

      {/* Local graph hint */}
      {localMode && !hoveredNode && (
        <div
          style={{
            position: 'absolute',
            top: '0.5rem',
            left: '50%',
            transform: 'translateX(-50%)',
            fontSize: '0.7rem',
            color: 'var(--text-secondary)',
            background: 'var(--bg-card, #181a1c)',
            padding: '0.3rem 0.6rem',
            borderRadius: '6px',
            border: '1px solid var(--border, #2d2d2d)',
            pointerEvents: 'none',
          }}
        >
          Hover a node to focus its local graph
        </div>
      )}

      {/* Local graph toggle + zoom / fit controls (bottom-right, Obsidian-style) */}
      <div
        style={{
          position: 'absolute',
          right: '0.5rem',
          bottom: '0.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
        }}
      >
        <button
          type="button"
          className={`btn btn-sm ${localMode ? 'btn-primary' : 'btn-ghost'}`}
          onClick={toggleLocalMode}
          aria-pressed={localMode}
          title="Local graph"
        >
          Local
        </button>
        {[
          { label: '+', title: 'Zoom in', onClick: handleZoomIn },
          { label: '−', title: 'Zoom out', onClick: handleZoomOut },
          { label: '⤢', title: 'Fit graph', onClick: handleFit },
        ].map((btn) => (
          <button
            key={btn.title}
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={btn.onClick}
            title={btn.title}
            aria-label={btn.title}
            style={{
              width: 28,
              height: 28,
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.85rem',
              lineHeight: 1,
            }}
          >
            {btn.label}
          </button>
        ))}
      </div>
    </div>
  );
};
