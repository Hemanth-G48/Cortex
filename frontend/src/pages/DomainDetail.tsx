import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { GapCard, GapPathPhaseView, LevelBadge } from '../components/kb/GapAnalysisComponents';
import { useGapNote } from '../hooks/useGapNote';
import { endpoints } from '../services/api';
import type { KbDomainDetail, KbDomainGapsResponse, KbDomainNode } from '../services/api';
import type { KbHealth } from '../services/api';

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

const docTypeIcon = (type: string) => {
  switch (type) {
    case 'md': return '📝';
    case 'pdf': return '📄';
    case 'txt': return '📃';
    case 'docx': return '📋';
    default: return '📄';
  }
};

/**
 * One domain/topic page: Course → Domain → Documents (+ domain gap analysis).
 *
 * The domain is the canonical Second Brain folder entity: documents come
 * straight from the folder (no manual assignment) and the gap analysis is
 * scoped to exactly this folder's notes. The analysis is persisted — opening
 * this page never re-runs it; only "Re-analyze" recomputes.
 */
export const DomainDetail = () => {
  const { courseId, domainId } = useParams<{ courseId: string; domainId: string }>();
  const navigate = useNavigate();
  const [domain, setDomain] = useState<KbDomainDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [gaps, setGaps] = useState<KbDomainGapsResponse | null>(null);
  const [gapsOpen, setGapsOpen] = useState(false);
  const [gapsLoading, setGapsLoading] = useState(false);
  const [gapsError, setGapsError] = useState<string | null>(null);
  const [openGap, setOpenGap] = useState<string | null>(null);
  const [staleIds, setStaleIds] = useState<number[]>([]);
  const { noteBusy, noteError, createNote, clearNoteError } = useGapNote();

  const folderId = Number(domainId);
  const courseIdNum = Number(courseId);

  const loadDomain = useCallback(async () => {
    if (!domainId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await endpoints.kb.folders.get(folderId);
      setDomain(data);
      // Health: badge stale/outdated documents in the list (defect #95).
      try {
        const h = await endpoints.kb.health() as KbHealth;
        setStaleIds(h.signals.stale_notes.document_ids);
      } catch { /* health endpoint optional */ }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [domainId, folderId]);

  useEffect(() => { void loadDomain(); }, [loadDomain]);

  const runGapAnalysis = async () => {
    setGapsOpen(true);
    setGapsLoading(true);
    setGapsError(null);
    clearNoteError();
    try {
      // Saved per folder: returns the stored analysis (cached: true) or
      // computes it once on the very first request (cached: false).
      const data = await endpoints.kb.folders.gaps(folderId);
      setGaps(data);
    } catch (e) {
      setGapsError((e as Error).message);
      setGaps(null);
    } finally {
      setGapsLoading(false);
    }
  };

  const reanalyzeGaps = async () => {
    setGapsLoading(true);
    setGapsError(null);
    clearNoteError();
    try {
      // The explicit user action that recomputes — never done automatically.
      const data = await endpoints.kb.folders.analyzeGaps(folderId);
      setGaps(data);
    } catch (e) {
      setGapsError((e as Error).message);
    } finally {
      setGapsLoading(false);
    }
  };

  const openDoc = (docId: number) => navigate(`/knowledge-base?doc=${docId}`);

  const courseTitle = domain?.course?.title ?? `Course #${courseIdNum}`;
  const courseLink = courseIdNum ? `/courses/${courseIdNum}` : '/courses';

  return (
    <div className="fade-in">
      <Header title={domain?.name ?? 'Domain'} />

      {/* Breadcrumb: Course → … → Domain */}
      <nav aria-label="Breadcrumb" className="domain-breadcrumb">
        <Link to={courseLink} className="domain-breadcrumb-link">{courseTitle}</Link>
        {(domain?.breadcrumb ?? []).map((b, i) => {
          const last = i === (domain?.breadcrumb.length ?? 0) - 1;
          return (
            <span key={b.id ?? `crumb-${i}`} className="domain-breadcrumb-item">
              <span className="domain-breadcrumb-sep">/</span>
              {last || !b.id ? (
                <span className="domain-breadcrumb-current">{b.name}</span>
              ) : (
                <button
                  type="button"
                  className="domain-breadcrumb-link"
                  onClick={() => navigate(`/courses/${courseIdNum}/domain/${b.id}`)}
                >
                  {b.name}
                </button>
              )}
            </span>
          );
        })}
      </nav>

      {loading ? (
        <div className="course-detail-loading">
          <div className="spinner" />
          <p>Loading domain…</p>
        </div>
      ) : error || !domain ? (
        <div className="notice notice-error" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span>{error || 'Domain not found'}</span>
          <span style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
            <button className="btn" onClick={() => void loadDomain()}>↻ Retry</button>
            <button className="btn btn-ghost" onClick={() => navigate(courseLink)}>← Back to {courseTitle}</button>
          </span>
        </div>
      ) : (
        <>
          {/* Domain header + gap action */}
          <div className="course-section">
            <div className="section-header">
              <h2>📂 {domain.name}</h2>
              <span className="badge badge-muted">{domain.path}</span>
            </div>
            {domain.description && <p className="gap-hint">{domain.description}</p>}
            <div className="course-detail-actions" style={{ marginTop: '0.75rem' }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => void runGapAnalysis()}
                disabled={gapsLoading}
              >
                {gapsLoading ? <span className="spinner spinner-sm" /> : <span className="emoji">🕳️</span>}
                {gapsLoading ? 'Analyzing…' : 'Gap Analysis'}
              </button>
              {gaps && gaps.cached && (
                <span className="badge badge-info" title="Reused from your saved analysis — not recomputed">
                  Saved {formatTime(gaps.analyzed_at)}
                </span>
              )}
            </div>
          </div>

          {/* ── Domain gap analysis results (persisted) ── */}
          {gapsOpen && (
            <div className="course-section" data-testid="domain-gap-analysis-panel">
              <div className="section-header">
                <h3>🕳️ {domain.name} — Gap Analysis</h3>
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
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setGapsOpen(false)}>Close</button>
              </div>

              {gaps && gaps.cached && (
                <div
                  className={`notice ${(gaps.new_notes_since_analysis ?? 0) > 0 ? 'notice-warning' : 'notice-info'}`}
                  data-testid="domain-gaps-cached-notice"
                  style={{ marginBottom: '0.75rem' }}
                >
                  Showing your saved analysis from <strong>{formatTime(gaps.analyzed_at)}</strong> — it is reused, not recomputed.
                  {(gaps.new_notes_since_analysis ?? 0) > 0 ? (
                    <>
                      {' '}<strong>{gaps.new_notes_since_analysis} new note{gaps.new_notes_since_analysis === 1 ? '' : 's'}</strong>{' '}
                      were added to this folder since — click <strong>Re-analyze</strong> to refresh.
                    </>
                  ) : (
                    <> Click <strong>Re-analyze</strong> to refresh it from your latest Second Brain data.</>
                  )}
                </div>
              )}

              {gapsLoading ? (
                <div className="course-detail-loading" style={{ padding: '1.5rem' }}>
                  <div className="spinner" />
                  <p>Comparing this folder's notes against {domain.name} target concepts…</p>
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
                  <div className="gap-summary-card">
                    <p className="gap-summary-text">{gaps.summary?.text ?? 'Gap analysis complete.'}</p>
                    <div className="gap-summary-meta">
                      {gaps.domain && <span className="badge badge-info">{gaps.domain}</span>}
                      {gaps.summary?.priorities && gaps.summary.priorities.length > 0 && (
                        <span className="gap-meta">Top priorities: {gaps.summary.priorities.join(', ')}</span>
                      )}
                      <span className="gap-meta">Based on {gaps.document_count} document(s) in this folder.</span>
                    </div>
                  </div>

                  {gaps.next && (
                    <div className="gap-block">
                      <h4>📚 Learn This Next</h4>
                      <GapCard
                        gap={gaps.next}
                        open
                        onToggle={() => {}}
                        onOpenDoc={openDoc}
                        onCreateNote={(g) => createNote(g, domain.name)}
                        noteBusy={noteBusy === gaps.next?.name}
                      />
                    </div>
                  )}

                  <div className="gap-block">
                    <h4>🧠 Your Strengths ({gaps.strengths?.length ?? 0})</h4>
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
                    <h4>⚠️ Knowledge Gaps ({gaps.gaps?.length ?? 0})</h4>
                    <div className="gap-list">
                      {(gaps.gaps ?? []).filter((g) => g.name !== gaps.next?.name).slice(0, 15).map((g) => (
                        <GapCard
                          key={g.name}
                          gap={g}
                          open={openGap === g.name}
                          onToggle={() => setOpenGap(openGap === g.name ? null : g.name)}
                          onOpenDoc={openDoc}
                          onCreateNote={(g) => createNote(g, domain.name)}
                          noteBusy={noteBusy === g.name}
                        />
                      ))}
                    </div>
                  </div>

                  {gaps.path && gaps.path.length > 0 && (
                    <div className="gap-block">
                      <h4>🛣️ Recommended Learning Path</h4>
                      <GapPathPhaseView
                        phases={gaps.path}
                        onOpenDoc={openDoc}
                        onCreateNote={(item) => createNote(item, domain.name)}
                        noteBusy={noteBusy}
                      />
                    </div>
                  )}

                  {gaps.coverage && (
                    <p className="gap-meta">
                      Evidence coverage: {gaps.coverage.known} of {gaps.coverage.total} target concepts have
                      evidence ({Math.round(gaps.coverage.percent)}%).
                    </p>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* ── Subdomains ── */}
          {domain.subfolders.length > 0 && (
            <div className="course-section" data-testid="domain-subfolders">
              <div className="section-header">
                <h3>📁 Subdomains</h3>
                <span className="badge">{domain.subfolders.length}</span>
              </div>
              <div className="course-domains-grid">
                {domain.subfolders.map((s: KbDomainNode) => (
                  <button
                    key={s.id}
                    type="button"
                    className="course-domain-card"
                    onClick={() => navigate(`/courses/${courseIdNum}/domain/${s.id}`)}
                    title={`Open ${s.name} — ${s.doc_count} document${s.doc_count === 1 ? '' : 's'}`}
                  >
                    <span className="course-domain-icon">📂</span>
                    <span className="course-domain-name">{s.name}</span>
                    <span className="badge badge-info">{s.doc_count} doc{s.doc_count === 1 ? '' : 's'}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Documents (direct children of the folder) ── */}
          <div className="course-section" data-testid="domain-documents">
            <div className="section-header">
              <h3>📄 Documents</h3>
              <span className="badge">{domain.documents.length} document{domain.documents.length === 1 ? '' : 's'}</span>
            </div>
            {domain.documents.length === 0 ? (
              <div className="notice notice-info">
                <strong>No documents in this folder yet.</strong>{' '}
                Add notes under <code>{domain.path}/</code> in your Second Brain, then hit
                Resync on the course page — they appear here automatically.
              </div>
            ) : (
              <div className="document-list">
                {domain.documents.map((doc) => (
                  <div key={doc.id} className="document-card" style={{ cursor: 'pointer' }} onClick={() => openDoc(doc.id)}>
                    <div className="document-card-header">
                      <div className="document-icon">{docTypeIcon(doc.doc_type)}</div>
                      <div className="document-info">
                        <h4 className="document-title">{doc.title}</h4>
                        <div className="document-meta">
                          {doc.path_rel && <span className="path">📁 {doc.path_rel}</span>}
                          {doc.char_count > 0 && <span>{doc.char_count.toLocaleString()} chars</span>}
                          {doc.reading_time_seconds && <span>⏱ {formatDuration(doc.reading_time_seconds)}</span>}
                          {doc.quality_score != null && <span>⭐ {Math.round(doc.quality_score * 100)}%</span>}
                          {staleIds.includes(doc.id) && (
                            <span className="badge badge-warning" style={{ marginLeft: '0.4rem' }}>⚠ stale</span>
                          )}
                        </div>
                      </div>
                      <div className="document-expand-icon">↗</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
