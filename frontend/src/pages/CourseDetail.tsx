import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { ErrorBoundary } from '../components/shared/ErrorBoundary';
import { KnowledgeGraphCanvas } from '../components/kb/KnowledgeGraphCanvas';
import { KIND_COLORS } from '../components/kb/graphConstants';
import { GapCard, GapHistoryView, GapPathPhaseView, LevelBadge } from '../components/kb/GapAnalysisComponents';
import { useGapNote } from '../hooks/useGapNote';
import { endpoints } from '../services/api';
import type {
  CourseContentResponse,
  CourseDocument,
  CourseGapsResponse,
  CourseTopicNode,
  GapHistorySnapshot,
} from '../services/api';

const formatTime = (iso?: string | null) => {
  if (!iso) return 'never';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? 'unknown' : d.toLocaleString();
};

const formatDuration = (seconds?: number | null) => {
  if (!seconds) return null;
  const mins = Math.round(seconds / 60);
  if (mins < 1) return '< 1 min';
  if (mins < 60) return `${mins} min`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return remainMins > 0 ? `${hrs}h ${remainMins}m` : `${hrs}h`;
};

const formatDate = (iso?: string | null) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
};

const docTypeIcon = (type: string) => {
  switch (type) {
    case 'md': return '📝';
    case 'pdf': return '📄';
    case 'txt': return '📃';
    case 'docx': return '📋';
    default: return '📄';
  }
};

/** Compact document card used inside topic nodes. */
const DocMiniCard = ({ doc, onOpen }: { doc: CourseDocument; onOpen: (id: number) => void }) => (
  <div className="course-doc-mini" onClick={() => onOpen(doc.id)} role="button" tabIndex={0}>
    <span className="document-icon">{docTypeIcon(doc.doc_type)}</span>
    <div className="course-doc-mini-body">
      <span className="course-doc-mini-title">{doc.title}</span>
      <span className="course-doc-mini-meta">
        {doc.char_count > 0 && <span>{doc.char_count.toLocaleString()} chars</span>}
        {doc.reading_time_seconds && <span>⏱ {formatDuration(doc.reading_time_seconds)}</span>}
        {doc.quality_score != null && <span>⭐ {Math.round(doc.quality_score * 100)}%</span>}
      </span>
    </div>
  </div>
);

/** Recursive topic/subtopic node with the documents that cover it. */
interface TopicNodeProps {
  node: CourseTopicNode;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  onOpenDoc: (id: number) => void;
  // Breadcrumb of the nearest folder-derived ancestor (folder topics only).
  folderPath?: string | null;
}

const TopicNodeView = ({ node, expanded, onToggle, onOpenDoc, folderPath = null }: TopicNodeProps) => {
  const isOpen = expanded.has(node.id);
  const hasChildren = node.children.length > 0;
  // Folder topics show their vault path (``Memory`` → ``Memory / Virtual
  // Memory``); heading topics keep the tree path from the nearest folder.
  const isFolder = node.origin === 'folder';
  const nodeFolderPath = isFolder
    ? (folderPath ? `${folderPath} / ${node.name}` : node.name)
    : folderPath;
  return (
    <div className={`course-topic-node level-${Math.min(node.level, 3)}`}>
      <div className="course-topic-row" onClick={() => onToggle(node.id)}>
        <span className="topic-caret">{isOpen ? '▾' : '▸'}</span>
        <span className="topic-icon">{isFolder ? '📁' : '📖'}</span>
        <span className="topic-name">{node.name}</span>
        {isFolder && nodeFolderPath && nodeFolderPath !== node.name && (
          <span className="topic-breadcrumb" title={`Vault folder: ${nodeFolderPath}`}>
            {nodeFolderPath}
          </span>
        )}
        <span className="badge badge-info">{node.documents.length} doc{node.documents.length === 1 ? '' : 's'}</span>
        {hasChildren && <span className="badge badge-muted">{node.children.length} sub{node.children.length === 1 ? '' : 's'}</span>}
      </div>
      {isOpen && (
        <div className="course-topic-children">
          {node.documents.map((doc) => (
            <DocMiniCard key={doc.id} doc={doc} onOpen={onOpenDoc} />
          ))}
          {node.children.map((child) => (
            <TopicNodeView
              key={child.id}
              node={child}
              expanded={expanded}
              onToggle={onToggle}
              onOpenDoc={onOpenDoc}
              folderPath={nodeFolderPath}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const CourseDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [content, setContent] = useState<CourseContentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Gap analysis
  const [gaps, setGaps] = useState<CourseGapsResponse | null>(null);
  const [gapsOpen, setGapsOpen] = useState(false);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [gapsError, setGapsError] = useState<string | null>(null);
  const [openGap, setOpenGap] = useState<string | null>(null);
  const [gapsHistory, setGapsHistory] = useState<GapHistorySnapshot[] | null>(null);
  const [gapsHistoryOpen, setGapsHistoryOpen] = useState(false);
  const [gapsHistoryLoading, setGapsHistoryLoading] = useState(false);
  const [gapsHistoryError, setGapsHistoryError] = useState<string | null>(null);
  const { noteBusy, noteError, createNote, clearNoteError } = useGapNote();

  // Resync
  const [resyncing, setResyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<{ kind: 'success' | 'error' | 'info'; text: string } | null>(null);

  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [expandedDoc, setExpandedDoc] = useState<number | null>(null);
  // Only auto-expand top-level topics on the very first load — never on reload
  // (which would undo the user's collapse choices).
  const didAutoExpandRef = useRef(false);

  const loadContent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await endpoints.courses.content(parseInt(id, 10));
      setContent(data);
      // Auto-expand top-level topics so the topic → documents mapping is
      // visible immediately (subtopics stay collapsed).
      if (!didAutoExpandRef.current) {
        didAutoExpandRef.current = true;
        setExpandedTopics(new Set(data.second_brain.topics.map((t) => t.id)));
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void loadContent(); }, [loadContent]);

  const loadGapsHistory = useCallback(async () => {
    if (!id) return;
    setGapsHistoryLoading(true);
    setGapsHistoryError(null);
    try {
      const res = await endpoints.courses.gapHistory(parseInt(id, 10));
      setGapsHistory(res.history ?? []);
    } catch (e) {
      setGapsHistoryError((e as Error).message);
      setGapsHistory([]);
    } finally {
      setGapsHistoryLoading(false);
    }
  }, [id]);

  const runGapAnalysis = async () => {
    if (!id) return;
    setGapsOpen(true);
    setGapsLoading(true);
    setGapsError(null);
    clearNoteError();
    try {
      // Saved per course: returns the stored analysis (cached: true) or
      // computes it once on the very first request (cached: false).
      const data = await endpoints.courses.gaps(parseInt(id, 10));
      setGaps(data);
      // A fresh analysis may have been recorded — refresh an open history
      // panel right away (a closed one refreshes via the freshness guard).
      if (gapsHistoryOpen) void loadGapsHistory();
    } catch (e) {
      setGapsError((e as Error).message);
      setGaps(null);
    } finally {
      setGapsLoading(false);
    }
  };

  const reanalyzeGaps = async () => {
    if (!id) return;
    setGapsLoading(true);
    setGapsError(null);
    clearNoteError();
    try {
      // The explicit user action that recomputes — never done automatically.
      const data = await endpoints.courses.analyzeGaps(parseInt(id, 10));
      setGaps(data);
      // Re-analyze records a new snapshot — refresh an open history panel
      // right away (a closed one refreshes via the freshness guard).
      if (gapsHistoryOpen) void loadGapsHistory();
    } catch (e) {
      setGapsError((e as Error).message);
    } finally {
      setGapsLoading(false);
    }
  };

  const toggleGapsHistory = async () => {
    if (!id) return;
    if (gapsHistoryOpen) {
      setGapsHistoryOpen(false);
      return;
    }
    setGapsHistoryOpen(true);
    // Reuse the loaded list only when it already covers the CURRENT analysis
    // (its newest snapshot matches ``gaps.analyzed_at``). After a re-analyze —
    // or if an older fetch resolved after one — the timestamps diverge and we
    // refetch instead of trusting possibly-stale data.
    const latest = gapsHistory && gapsHistory.length > 0 ? gapsHistory[gapsHistory.length - 1].analyzed_at : null;
    if (gapsHistory && latest === gaps?.analyzed_at) return;
    await loadGapsHistory();
  };

  const runResync = async () => {
    if (!id) return;
    setResyncing(true);
    setSyncMsg(null);
    try {
      const result = await endpoints.courses.resync(parseInt(id, 10));
      if (result.course_removed) {
        // The stale course row no longer exists — keep the user informed, then
        // leave the dead page instead of leaving them stranded on it.
        setSyncMsg({
          kind: 'info',
          text: 'This course was removed by the resync (its `course:` tag no longer resolves). Taking you back to Courses…',
        });
        window.setTimeout(() => navigate('/courses'), 1600);
      } else {
        if (result.content) setContent(result.content);
        const kb = result.kb;
        let text = `Second Brain synced — ${kb.created} created, ${kb.updated} updated, ${kb.removed} removed.`;
        if (result.classroom && !result.classroom.error) {
          const src = result.classroom.source === 'mock' ? ' (offline demo)' : '';
          text += ` Google Classroom: ${result.classroom.courses ?? 0} course(s), ${result.classroom.assignments ?? 0} assignment(s)${src}.`;
        } else if (result.classroom?.error) {
          text += ` Classroom sync failed: ${result.classroom.error}`;
        }
        setSyncMsg({ kind: 'success', text });
      }
    } catch (e) {
      setSyncMsg({ kind: 'error', text: (e as Error).message });
    } finally {
      setResyncing(false);
    }
  };

  const toggleTopic = (topicId: string) => {
    setExpandedTopics((prev) => {
      const next = new Set(prev);
      if (next.has(topicId)) next.delete(topicId);
      else next.add(topicId);
      return next;
    });
  };

  const openDoc = (docId: number) => navigate(`/knowledge-base?doc=${docId}`);

  // Derived stats
  const documents = useMemo(() => content?.second_brain.documents ?? [], [content]);
  const topics = useMemo(() => content?.second_brain.topics ?? [], [content]);
  const concepts = useMemo(() => content?.second_brain.concepts ?? [], [content]);
  const totalReadingTime = useMemo(
    () => documents.reduce((acc, d) => acc + (d.reading_time_seconds || 0), 0),
    [documents],
  );
  const avgQuality = useMemo(() => {
    const scored = documents.filter((d) => d.quality_score != null);
    if (scored.length === 0) return null;
    const sum = scored.reduce((acc, d) => acc + (d.quality_score || 0), 0);
    return Math.round((sum / scored.length) * 100) / 100;
  }, [documents]);

  // Subject knowledge graph → canvas props. Guarded so a malformed payload
  // (missing/null nodes/edges) degrades to an empty graph instead of crashing.
  const graphNodes = useMemo(() => {
    if (!content) return [];
    const nodes = content.second_brain.graph?.nodes ?? [];
    return nodes.map((n) => ({
      id: n.id,
      label: n.label,
      kind: n.kind,
      doc_type: n.doc_type ?? null,
      status: n.status ?? null,
      degree: n.degree ?? 0,
      color: KIND_COLORS[n.kind] ?? '#6b7280',
    }));
  }, [content]);
  const graphEdges = useMemo(() => {
    if (!content) return [];
    const edges = content.second_brain.graph?.edges ?? [];
    return edges.map((e) => ({
      source: e.source,
      target: e.target,
      relation: e.relation,
      weight: e.weight,
      provenance: e.provenance,
    }));
  }, [content]);

  if (loading) {
    return (
      <div>
        <Header title="Loading..." />
        <div className="course-detail-loading">
          <div className="spinner" />
          <p>Loading subject details and Second Brain content...</p>
        </div>
      </div>
    );
  }

  if (error || !content) {
    return (
      <div>
        <Header title="Error" />
        <div className="notice notice-error" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <span>{error || 'Course not found'}</span>
          <span style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
            <button className="btn" onClick={() => void loadContent()}>
              ↻ Retry
            </button>
            <button className="btn btn-ghost" onClick={() => navigate('/courses')}>
              ← Back to Courses
            </button>
          </span>
        </div>
      </div>
    );
  }

  const course = content.course;
  const isSecondBrain =
    course.source_type === 'kb_tag' || course.source_type === 'kb_folder' || !!course.kb_tag_id;
  const sourceLabel = course.source_type === 'classroom' ? 'Google Classroom' : isSecondBrain ? 'Second Brain' : 'Manual';
  const sourceEmoji = course.source_type === 'classroom' ? '🏫' : isSecondBrain ? '🧠' : '✏️';

  const topicGaps = (gaps?.topics ?? []).filter((g) => g.is_gap).sort((a, b) => a.coverage - b.coverage);
  const conceptGaps = gaps?.concepts ?? [];

  return (
    // A render failure in ANY section (graph, topic tree, …) must never blank
    // the whole page — the boundary shows a recoverable fallback instead.
    <ErrorBoundary
      resetKey={course.id}
      fallback={(_error, reset) => (
        <div>
          <Header title={course.title} />
          <div className="course-section">
            <div className="section-header">
              <h2>⚠️ Something went wrong</h2>
            </div>
            <div className="notice notice-error">
              The subject page hit an unexpected error while rendering.
              <button className="btn" onClick={reset} style={{ marginLeft: '1rem' }}>
                ↻ Try again
              </button>
              <button className="btn btn-ghost" onClick={() => navigate('/courses')} style={{ marginLeft: '0.5rem' }}>
                ← Back to Courses
              </button>
            </div>
          </div>
        </div>
      )}
    >
      <div>
        <Header title={course.title} />

        {/* Navigation bar */}
      <div className="course-detail-nav">
        <button className="btn btn-ghost" onClick={() => navigate('/courses')}>
          ← Back to Courses
        </button>
        <div className="course-detail-badges">
          <span className={`badge badge-${course.status === 'Completed' ? 'success' : course.status === 'In progress' ? 'warning' : 'info'}`}>
            {course.status}
          </span>
          <span className="badge badge-muted">{sourceEmoji} {sourceLabel}</span>
        </div>
      </div>

      {/* Action bar: Gap Analysis + Resync */}
      <div className="course-detail-actions">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => void runGapAnalysis()}
          disabled={gapsLoading || resyncing}
        >
          {gapsLoading ? <span className="spinner spinner-sm" /> : <span className="emoji">🕳️</span>}
          {gapsLoading ? 'Analyzing…' : 'Gap Analysis'}
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void runResync()}
          disabled={resyncing || gapsLoading}
        >
          {resyncing ? <span className="spinner spinner-sm" /> : <span className="emoji">🔄</span>}
          {resyncing ? 'Resyncing…' : 'Resync'}
        </button>
      </div>

      {syncMsg && (
        <div className={`notice notice-${syncMsg.kind}`} data-testid="resync-message">
          {syncMsg.text}
        </div>
      )}

      {/* Stats grid — note: no Progress tile by design */}
      <div className="stat-grid">
        <div className="stat-tile">
          <div className="label">Assignments</div>
          <div className="value">{course.current_assignment}/{course.total_assignments}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Documents</div>
          <div className="value">{documents.length}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Topics</div>
          <div className="value">{topics.length}</div>
        </div>
        {totalReadingTime > 0 && (
          <div className="stat-tile">
            <div className="label">Reading Time</div>
            <div className="value">{formatDuration(totalReadingTime)}</div>
          </div>
        )}
        {avgQuality != null && (
          <div className="stat-tile">
            <div className="label">Avg Quality</div>
            <div className="value">{Math.round(avgQuality * 100)}%</div>
          </div>
        )}
      </div>

      {/* ── Gap Analysis results (redesigned actionable engine) ── */}
      {gapsOpen && (
        <div className="course-section" data-testid="gap-analysis-panel">
          <div className="section-header">
            <h2>🕳️ Gap Analysis</h2>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void reanalyzeGaps()}
              disabled={gapsLoading}
              title="Recompute this analysis from your latest Second Brain data"
            >
              {gapsLoading ? <span className="spinner spinner-sm" /> : '↻'}
              Re-analyze
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void toggleGapsHistory()}
              disabled={gapsHistoryLoading}
              title="How this subject's gaps changed across past analyses"
            >
              {gapsHistoryLoading ? <span className="spinner spinner-sm" /> : '🗂'}
              {gapsHistoryOpen ? 'Hide History' : 'History'}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setGapsOpen(false)}>Close</button>
          </div>

          {gaps && gaps.cached && (
            <div
              className={`notice ${(gaps.new_notes_since_analysis ?? 0) > 0 ? 'notice-warning' : 'notice-info'}`}
              data-testid="gaps-cached-notice"
              style={{ marginBottom: '0.75rem' }}
            >
              Showing your saved analysis from{' '}
              <strong>{formatTime(gaps.analyzed_at)}</strong> — it is reused, not recomputed.
              {(gaps.new_notes_since_analysis ?? 0) > 0 ? (
                <>
                  {' '}<strong>{gaps.new_notes_since_analysis} new note{gaps.new_notes_since_analysis === 1 ? '' : 's'}</strong>{' '}
                  were added to this subject since — click <strong>Re-analyze</strong> to refresh.
                </>
              ) : (
                <> Click <strong>Re-analyze</strong> to refresh it from your latest Second Brain data.</>
              )}
            </div>
          )}

          {gapsHistoryOpen && (
            <div className="gap-history-wrap" style={{ marginBottom: '0.75rem' }}>
              {gapsHistoryLoading ? (
                <div className="course-detail-loading" style={{ padding: '1rem' }}>
                  <div className="spinner" />
                  <p>Loading analysis history…</p>
                </div>
              ) : gapsHistoryError ? (
                <div className="notice notice-error">{gapsHistoryError}</div>
              ) : (
                <GapHistoryView snapshots={gapsHistory ?? []} />
              )}
            </div>
          )}

          {gapsLoading ? (
            <div className="course-detail-loading" style={{ padding: '1.5rem' }}>
              <div className="spinner" />
              <p>Comparing your Second Brain evidence against this subject's target concepts…</p>
            </div>
          ) : gapsError ? (
            <div className="notice notice-error">{gapsError}</div>
          ) : gaps ? (
            <div className="gap-analysis-body">
              {noteError && (
                <div className="notice notice-error" style={{ marginBottom: '0.75rem' }}>
                  Could not create the note: {noteError}
                </div>
              )}
              {gaps.gaps ? (
                /* ── New: actionable learning/skill-gap engine ── */
                <>
                  <div className="gap-summary-card">
                    <p className="gap-summary-text">{gaps.summary?.text ?? 'Gap analysis complete.'}</p>
                    <div className="gap-summary-meta">
                      {gaps.domain && <span className="badge badge-info">{gaps.domain}</span>}
                      {gaps.summary?.priorities && gaps.summary.priorities.length > 0 && (
                        <span className="gap-meta">Top priorities: {gaps.summary.priorities.join(', ')}</span>
                      )}
                      <span className="gap-meta">Based on {gaps.document_count} Second Brain document(s).</span>
                    </div>
                  </div>

                  {gaps.next && (
                    <div className="gap-block">
                      <h3>📚 Learn This Next</h3>
                      <p className="gap-hint">The single highest-value concept to study right now.</p>
                      <GapCard
                        gap={gaps.next}
                        open
                        onToggle={() => {}}
                        onOpenDoc={openDoc}
                        onCreateNote={(g) => createNote(g, course.title)}
                        noteBusy={noteBusy === gaps.next?.name}
                      />
                    </div>
                  )}

                  <div className="gap-block">
                    <h3>🧠 Your Strengths ({gaps.strengths?.length ?? 0})</h3>
                    <p className="gap-hint">Concepts with real evidence of understanding in this area.</p>
                    {gaps.strengths && gaps.strengths.length > 0 ? (
                      <div className="gap-strength-chips">
                        {gaps.strengths.map((s) => (
                          <span key={s.name} className="gap-strength-chip" title={s.why ?? ''}>
                            ✓ {s.name} <LevelBadge level={s.level} />
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="gap-hint">No concepts with strong evidence yet — the path below starts from zero.</p>
                    )}
                  </div>

                  <div className="gap-block">
                    <h3>⚠️ Knowledge Gaps ({gaps.gaps.length})</h3>
                    <p className="gap-hint">
                      Ranked by importance × how little evidence you have. Open a gap for why it matters,
                      prerequisites, learning steps, practice, and linked notes.
                    </p>
                    <div className="gap-list">
                      {gaps.gaps.filter((g) => g.name !== gaps.next?.name).slice(0, 15).map((g) => (
                        <GapCard
                          key={g.name}
                          gap={g}
                          open={openGap === g.name}
                          onToggle={() => setOpenGap(openGap === g.name ? null : g.name)}
                          onOpenDoc={openDoc}
                          onCreateNote={(g) => createNote(g, course.title)}
                          noteBusy={noteBusy === g.name}
                        />
                      ))}
                    </div>
                  </div>

                  {gaps.path && gaps.path.length > 0 && (
                    <div className="gap-block">
                      <h3>🛣️ Recommended Learning Path</h3>
                      <p className="gap-hint">
                        Prerequisite-first order — foundations always come before advanced topics. Each step links
                        to the Second Brain documents that mention it, and can draft a study note.
                      </p>
                      <GapPathPhaseView
                        phases={gaps.path}
                        onOpenDoc={openDoc}
                        onCreateNote={(item) => createNote(item, course.title)}
                        noteBusy={noteBusy}
                      />
                    </div>
                  )}

                  {gaps.coverage && (
                    <p className="gap-meta">
                      Evidence coverage: {gaps.coverage.known} of {gaps.coverage.total} target concepts have
                      evidence ({Math.round(gaps.coverage.percent)}%). Percentages are secondary — the gaps
                      and path above tell you what to do next.
                    </p>
                  )}
                </>
              ) : (
                /* ── Legacy fallback (old backend payload) ── */
                <>
                  <div className="gap-meta">
                    Based on {gaps.document_count} Second Brain document(s) for this subject.
                  </div>
                  {topicGaps.length > 0 && (
                    <div className="gap-block">
                      <h3>📚 Topics with thin coverage ({topicGaps.length})</h3>
                      <p className="gap-hint">
                        Topics below {Math.round(gaps.threshold * 100)}% document coverage.
                      </p>
                      <div className="gap-list">
                        {topicGaps.slice(0, 20).map((g) => (
                          <div key={g.normalized} className="gap-row">
                            <span className="gap-name" title={g.topic}>{g.topic}</span>
                            <div className="gap-bar-track">
                              <div className="gap-bar" style={{ width: `${Math.min(100, g.coverage * 100)}%` }} />
                            </div>
                            <span className="gap-value">{g.documents} doc{`${g.documents === 1 ? '' : 's'}`} · {Math.round(g.coverage * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="gap-block">
                    <h3>💡 Concept-level gaps ({conceptGaps.length})</h3>
                    {conceptGaps.length === 0 ? (
                      <p className="gap-hint">No concept gaps detected for this subject.</p>
                    ) : (
                      <div className="gap-list">
                        {conceptGaps.slice(0, 20).map((g) => (
                          <div key={g.concept_id} className="gap-row gap-row-concept">
                            <span className="gap-name" title={g.definition ?? ''}>{g.concept}</span>
                            <div className="gap-bar-track">
                              <div className="gap-bar" style={{ width: `${Math.min(100, g.score * 100)}%` }} />
                            </div>
                            <span className="gap-value">
                              {g.evidence.quiz_errors} err · {g.evidence.retrieval_misses} miss · strength {Math.round(g.evidence.strength * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {gaps.classroom.total > 0 && (
                    <div className="gap-block">
                      <h3>🏫 Classroom signals ({gaps.classroom.pending} pending of {gaps.classroom.total})</h3>
                      <div className="gap-list">
                        {gaps.classroom.assignments.filter((a) => a.status !== 'Completed').slice(0, 10).map((a) => (
                          <div key={a.id} className="gap-row">
                            <span className="gap-name">{a.title}</span>
                            <span className="gap-value">{a.status} · due {formatDate(a.due_date)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* ══════════ SECOND BRAIN ══════════ */}
      <div className="course-source-section second-brain-section">
        <div className="course-source-header">
          <h2>🧠 Second Brain</h2>
          <span className="badge badge-muted">{documents.length} documents · {concepts.length} concepts</span>
        </div>

        {/* ── Domains (folder hierarchy — the canonical organization) ── */}
        {/* The Second Brain folder tree below the course root defines the
            domains. Folders determine organization: clicking a domain opens
            its own page with the folder's documents + domain gap analysis. */}
        {(content.second_brain.domains ?? []).length > 0 && (
          <div className="course-section" data-testid="domains-grid">
            <div className="section-header">
              <h3>📂 Domains</h3>
              <span className="badge">{(content.second_brain.domains ?? []).length} folder{(content.second_brain.domains ?? []).length === 1 ? '' : 's'}</span>
            </div>
            <div className="course-domains-grid">
              {(content.second_brain.domains ?? []).map((d) => (
                <button
                  key={d.id}
                  type="button"
                  className="course-domain-card"
                  onClick={() => navigate(`/courses/${course.id}/domain/${d.id}`)}
                  title={`Open ${d.name} — ${d.doc_count} document${d.doc_count === 1 ? '' : 's'}`}
                >
                  <span className="course-domain-icon">📂</span>
                  <span className="course-domain-name">{d.name}</span>
                  {d.description && <span className="course-domain-desc">{d.description}</span>}
                  <span className="badge badge-info">
                    {d.doc_count} doc{d.doc_count === 1 ? '' : 's'}
                  </span>
                  <span className="course-domain-gap">🕳️ Gap Analysis</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Topics & Subtopics with related documents */}
        <div className="course-section">
          <div className="section-header">
            <h3>📚 Topics & Subtopics</h3>
            <span className="badge">{topics.length} topics</span>
          </div>
          {topics.length === 0 ? (
            <div className="notice notice-info">
              <strong>No topics yet.</strong> Add notes under a <code>course:{course.title}</code> tag or in the
              subject's vault folder, then hit <strong>Resync</strong> — topics are derived from the notes' headings.
            </div>
          ) : (
            <div className="course-topic-tree">
              {topics.map((topic) => (
                <TopicNodeView key={topic.id} node={topic} expanded={expandedTopics} onToggle={toggleTopic} onOpenDoc={openDoc} />
              ))}
            </div>
          )}
        </div>

        {/* Unorganized / flat notes */}
        {content.second_brain.unorganized_documents.length > 0 && (
          <div className="course-section">
            <div className="section-header">
              <h3>🗒️ Notes without headings</h3>
              <span className="badge">{content.second_brain.unorganized_documents.length}</span>
            </div>
            <div className="document-list">
              {content.second_brain.unorganized_documents.map((doc) => (
                <DocMiniCard key={doc.id} doc={doc} onOpen={openDoc} />
              ))}
            </div>
          </div>
        )}

        {/* Related concepts */}
        {concepts.length > 0 && (
          <div className="course-section">
            <div className="section-header">
              <h3>🔗 Related Concepts</h3>
              <span className="badge">{concepts.length} concepts</span>
            </div>
            <div className="course-concepts-grid">
              {concepts.map((c) => (
                <div key={c.concept_id} className="course-concept-chip" title={c.definition ?? ''}>
                  <span className="concept-name">{c.name}</span>
                  <span className="concept-count">{c.document_count} doc{c.document_count === 1 ? '' : 's'}</span>
                  {c.sources.length > 0 && (
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => openDoc(c.sources[0].document_id)}>
                      📄 {c.sources[0].title}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Knowledge graph (subject-scoped) */}
        <div className="course-section">
          <div className="section-header">
            <h3>🕸️ Knowledge Graph</h3>
            <span className="badge">{graphNodes.length} nodes · {graphEdges.length} edges</span>
          </div>
          {/* Key the boundary off the data itself so a successful Resync (new
              graph payload, same course id) resets it and the graph recovers
              without leaving the page. */}
          <ErrorBoundary
            resetKey={`${course.id}:${content.second_brain.graph?.total_nodes ?? 0}:${content.second_brain.graph?.total_edges ?? 0}`}
            fallback={(_error, reset) => (
              <div className="notice notice-warning" role="alert" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <strong>The knowledge graph failed to render.</strong>{' '}
                <span>The rest of the subject content below is unaffected.</span>
                <button className="btn btn-ghost btn-sm" onClick={reset}>
                  ↻ Retry graph
                </button>
              </div>
            )}
          >
            <KnowledgeGraphCanvas nodes={graphNodes} edges={graphEdges} height={420} onNodeClick={(n) => {
              if (n.id.startsWith('doc:')) openDoc(parseInt(n.id.slice(4), 10));
            }} />
          </ErrorBoundary>
        </div>

        {/* All documents (metadata-rich) */}
        <div className="course-section">
          <div className="section-header">
            <h3>📄 Documents</h3>
            <span className="badge">{documents.length} documents</span>
          </div>
          {documents.length === 0 ? (
            <div className="notice notice-info">
              <strong>No documents found.</strong>
              <p>
                Tag Second Brain notes with <code>course:{course.title}</code> or keep them in the subject's
                vault folder, then hit <strong>Resync</strong>.
              </p>
            </div>
          ) : (
            <div className="document-list">
              {documents.map((doc) => {
                const isExpanded = expandedDoc === doc.id;
                return (
                  <div key={doc.id} className={`document-card ${isExpanded ? 'document-card-expanded' : ''}`}>
                    <div
                      className="document-card-header"
                      onClick={() => setExpandedDoc(isExpanded ? null : doc.id)}
                    >
                      <div className="document-icon">{docTypeIcon(doc.doc_type)}</div>
                      <div className="document-info">
                        <h4 className="document-title">{doc.title}</h4>
                        <div className="document-meta">
                          {doc.path_rel && <span className="path">📁 {doc.path_rel}</span>}
                          {doc.char_count > 0 && <span>{doc.char_count.toLocaleString()} chars</span>}
                          {doc.reading_time_seconds && <span>⏱ {formatDuration(doc.reading_time_seconds)}</span>}
                          {doc.quality_score != null && <span>⭐ {Math.round(doc.quality_score * 100)}%</span>}
                          {doc.author && <span>✍️ {doc.author}</span>}
                          {doc.updated_at && <span>Updated {formatTime(doc.updated_at)}</span>}
                        </div>
                      </div>
                      <div className="document-expand-icon">{isExpanded ? '▾' : '▸'}</div>
                    </div>
                    {isExpanded && (
                      <div className="document-expanded-content">
                        {doc.outline && doc.outline.length > 0 && (
                          <div className="document-outline">
                            <h5>📑 Outline</h5>
                            <ul className="outline-list">
                              {doc.outline.map((item, i) => (
                                <li key={i} className={`outline-item outline-level-${item.level}`}>{item.text}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {doc.tags && doc.tags.length > 0 && (
                          <div className="document-tags">
                            <h5>🏷️ Tags</h5>
                            <div className="course-tags-wrap">
                              {doc.tags.map((tag, i) => <span key={i} className="course-tag-chip">{tag}</span>)}
                            </div>
                          </div>
                        )}
                        {doc.wikilinks && doc.wikilinks.length > 0 && (
                          <div className="document-wikilinks">
                            <h5>🔗 Linked Notes</h5>
                            <div className="course-tags-wrap">
                              {doc.wikilinks.map((link, i) => <span key={i} className="course-tag-chip wikilink-chip">{link}</span>)}
                            </div>
                          </div>
                        )}
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => openDoc(doc.id)}>
                          Open in Second Brain ↗
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ══════════ GOOGLE CLASSROOM ══════════ */}
      <div className="course-source-section classroom-section">
        <div className="course-source-header">
          <h2>🏫 Google Classroom</h2>
          <span className="badge badge-muted">
            {content.classroom.total_assignments} assignment{content.classroom.total_assignments === 1 ? '' : 's'}
            {content.classroom.linked ? ' · linked' : ''}
          </span>
        </div>

        <div className="course-section">
          <div className="section-header">
            <h3>📝 Assignments</h3>
            <span className="badge">{content.classroom.assignments.length}</span>
          </div>

          {content.classroom.assignments.length === 0 ? (
            <div className="notice notice-info">
              <strong>No assignments synced for this course.</strong>
              <p>
                {content.classroom.linked
                  ? 'This course is linked to Google Classroom. Hit Resync to pull its latest assignments (requires a live Classroom connection).'
                  : 'This course has no Classroom link. Connect Google Classroom and sync its courses to populate assignments here.'}
              </p>
            </div>
          ) : (
            <div className="classroom-assignment-list">
              {content.classroom.assignments.map((a) => (
                <div key={a.id} className="classroom-assignment-row">
                  <span className={`badge badge-${a.status === 'Completed' ? 'success' : a.status === 'In progress' ? 'warning' : 'info'}`}>
                    {a.status}
                  </span>
                  <span className="assignment-title">{a.title}</span>
                  {a.description && <span className="assignment-desc">{a.description}</span>}
                  <span className="assignment-due">Due {formatDate(a.due_date)}</span>
                </div>
              ))}
            </div>
          )}

          {content.classroom.course_url && (
            <div style={{ marginTop: '0.75rem' }}>
              <a href={content.classroom.course_url} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                Open in Google Classroom ↗
              </a>
            </div>
          )}

          <p className="gap-hint" style={{ marginTop: '0.75rem' }}>
            Classroom sync currently pulls courses and assignments. Course materials and announcements
            aren't synced into the app yet — use “Open in Google Classroom” for the full course stream.
          </p>
        </div>
      </div>

      {/* Course Info Section */}
      <div className="course-section">
        <div className="section-header">
          <h2>ℹ️ Course Information</h2>
        </div>
        <div className="course-info-panel">
          {course.description && (
            <div className="info-row">
              <span className="info-label">Description:</span>
              <span className="info-value">{course.description}</span>
            </div>
          )}
          {course.color && (
            <div className="info-row">
              <span className="info-label">Accent:</span>
              <span className="info-value">
                <span className="course-color-dot" style={{ background: course.color }} /> {course.color}
              </span>
            </div>
          )}
          <div className="info-row">
            <span className="info-label">Source:</span>
            <span className="info-value">{sourceEmoji} {sourceLabel}</span>
          </div>
          {course.google_id && (
            <div className="info-row">
              <span className="info-label">Google ID:</span>
              <span className="info-value">{course.google_id}</span>
            </div>
          )}
          {course.classroom_url && (
            <div className="info-row">
              <span className="info-label">Classroom:</span>
              <a href={course.classroom_url} target="_blank" rel="noopener noreferrer">
                Open in Google Classroom ↗
              </a>
            </div>
          )}
          <div className="info-row">
            <span className="info-label">KB Document Count:</span>
            <span className="info-value">{course.kb_document_count}</span>
          </div>
          {course.kb_tag_id && (
            <div className="info-row">
              <span className="info-label">KB Tag ID:</span>
              <span className="info-value">#{course.kb_tag_id}</span>
            </div>
          )}
        </div>
      </div>
      </div>
    </ErrorBoundary>
  );
};
