import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { GapCard, GapHistoryView, GapPathPhaseView, LevelBadge } from '../components/kb/GapAnalysisComponents';
import { useGapNote } from '../hooks/useGapNote';
import { endpoints } from '../services/api';
import type { GapAnalysisResponse, GapGoalInfo, GapHistorySnapshot } from '../services/api';

const statusColor = (status: string) => {
  if (status === 'Strong') return 'var(--success)';
  if (status === 'Developing') return 'var(--warning)';
  return 'var(--danger)';
};

const formatTime = (iso?: string | null) => {
  if (!iso) return 'never';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? 'unknown' : d.toLocaleString();
};

/**
 * Goal/career-level Gap Analysis — the redesigned actionable engine.
 *
 * Picks a goal (e.g. "Cybersecurity CTF"), evaluates the user's actual Second
 * Brain evidence against every concept in the goal's domains, and answers:
 * what do I know → what am I missing → why → what should I learn next →
 * what learning path should I follow.
 */
export const GapAnalysis = () => {
  const navigate = useNavigate();
  const [goals, setGoals] = useState<GapGoalInfo[]>([]);
  const [selected, setSelected] = useState<string>('ctf');
  const [result, setResult] = useState<GapAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openGap, setOpenGap] = useState<string | null>(null);
  const [history, setHistory] = useState<GapHistorySnapshot[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const { noteBusy, noteError, createNote, clearNoteError } = useGapNote();
  // Mirrors ``historyOpen`` without making ``run``/``reanalyze`` (used by the
  // ``useEffect`` on [selected, run]) change identity when the panel toggles —
  // otherwise toggling History would re-trigger a goal analysis refetch.
  const historyOpenRef = useRef(false);
  historyOpenRef.current = historyOpen;

  const loadGoals = useCallback(async () => {
    try {
      const res = await endpoints.kb.gaps.domains();
      setGoals(res.goals ?? []);
      // Keep the current selection unless it's no longer offered (functional
      // update avoids a stale ``selected`` closure; the goals list is static
      // and only needs loading once).
      setSelected((cur) =>
        res.goals.length > 0 && !res.goals.some((g) => g.key === cur) ? res.goals[0].key : cur
      );
    } catch {
      /* goals endpoint unavailable — keep the default selection */
    }
  }, []);

  useEffect(() => { void loadGoals(); }, [loadGoals]);

  const loadGoalHistory = useCallback(async () => {
    if (!selected) return;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await endpoints.kb.gaps.goalHistory(selected);
      setHistory(res.history ?? []);
    } catch (e) {
      setHistoryError((e as Error).message);
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [selected]);

  const run = useCallback(async (goal: string) => {
    setLoading(true);
    setError(null);
    setOpenGap(null);
    clearNoteError();
    try {
      setResult(await endpoints.kb.gaps.goal(goal));
      // A fresh analysis may have been recorded — refresh an open history
      // panel right away (a closed one refreshes via the freshness guard).
      if (historyOpenRef.current) void loadGoalHistory();
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [clearNoteError, loadGoalHistory]);

  // The explicit user action that recomputes — never done automatically.
  const reanalyze = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setOpenGap(null);
    clearNoteError();
    try {
      setResult(await endpoints.kb.gaps.analyzeGoal(selected));
      // Re-analyze records a new snapshot — refresh an open history panel
      // right away (a closed one refreshes via the freshness guard).
      if (historyOpenRef.current) void loadGoalHistory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selected, clearNoteError, loadGoalHistory]);

  const toggleGoalHistory = useCallback(async () => {
    if (!selected) return;
    if (historyOpen) {
      setHistoryOpen(false);
      return;
    }
    setHistoryOpen(true);
    // Reuse the loaded list only when it already covers the CURRENT analysis
    // (its newest snapshot matches ``result.analyzed_at``). After a re-analyze
    // or goal switch — or if an older fetch resolved after one — the
    // timestamps diverge and we refetch instead of trusting stale data.
    const latest = history && history.length > 0 ? history[history.length - 1].analyzed_at : null;
    if (history && latest === result?.analyzed_at) return;
    await loadGoalHistory();
  }, [selected, history, historyOpen, result?.analyzed_at, loadGoalHistory]);

  useEffect(() => { if (selected) void run(selected); }, [selected, run]);

  const openDoc = (docId: number) => navigate(`/knowledge-base?doc=${docId}`);

  return (
    <div className="page-section">
      <Header title="🎯 Gap Analysis" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Goal-level learning gap engine: your Second Brain evidence vs. the knowledge a goal requires —
        what you know, what you are missing, why it matters, and the exact path to follow.
      </p>

      {/* Goal picker */}
      {goals.length > 0 && (
        <div className="gap-goal-picker">
          {goals.map((g) => (
            <button
              key={g.key}
              type="button"
              className={`gap-goal-chip ${selected === g.key ? 'gap-goal-chip-active' : ''}`}
              onClick={() => setSelected(g.key)}
              title={g.description}
            >
              {g.title}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="course-detail-loading" style={{ padding: '2rem' }}>
          <div className="spinner" />
          <p>Comparing your Second Brain evidence against the goal's domains…</p>
        </div>
      ) : (
        <>
          {error && (
            <div className="notice notice-error" style={{ marginTop: '1rem' }}>
              {error}
            </div>
          )}
          {result && (() => {
            // Normalize the result so no payload drift can crash the page —
            // every array/object read below is guaranteed to exist.
            const r = {
              ...result,
              summary: result.summary ?? { text: '', priorities: [], strong_areas: [] },
              strengths: result.strengths ?? [],
              gaps: result.gaps ?? [],
              path: result.path ?? [],
              domain_breakdown: result.domain_breakdown ?? [],
              coverage: result.coverage ?? { known: 0, gaps: 0, total: 0, percent: 0 },
            };
            return (
            <div className="gap-analysis-body" style={{ marginTop: '1rem' }}>
              {/* Re-analyze — the explicit recompute action (results are saved
                  and reused; this is the only way to refresh them). */}
              <div className="gap-analysis-actions">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void reanalyze()}
                  title="Recompute this analysis from your latest Second Brain data"
                >
                  ↻ Re-analyze
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void toggleGoalHistory()}
                  disabled={historyLoading}
                  title="How this goal's gaps changed across past analyses"
                >
                  {historyLoading ? <span className="spinner spinner-sm" /> : '🗂'}
                  {historyOpen ? 'Hide History' : 'History'}
                </button>
              </div>

              {result.cached && (
                <div
                  className={`notice ${(result.new_notes_since_analysis ?? 0) > 0 ? 'notice-warning' : 'notice-info'}`}
                  data-testid="gaps-cached-notice"
                  style={{ marginBottom: '0.75rem' }}
                >
                  Showing your saved analysis from{' '}
                  <strong>{formatTime(result.analyzed_at)}</strong> — it is reused, not recomputed.
                  {(result.new_notes_since_analysis ?? 0) > 0 ? (
                    <>
                      {' '}<strong>{result.new_notes_since_analysis} new note{result.new_notes_since_analysis === 1 ? '' : 's'}</strong>{' '}
                      were added to your Second Brain since — click <strong>Re-analyze</strong> to refresh.
                    </>
                  ) : (
                    <> Click <strong>Re-analyze</strong> to refresh it from your latest Second Brain data.</>
                  )}
                </div>
              )}

              {historyOpen && (
                <div className="gap-history-wrap" style={{ marginBottom: '0.75rem' }}>
                  {historyLoading ? (
                    <div className="course-detail-loading" style={{ padding: '1rem' }}>
                      <div className="spinner" />
                      <p>Loading analysis history…</p>
                    </div>
                  ) : historyError ? (
                    <div className="notice notice-error">{historyError}</div>
                  ) : (
                    <GapHistoryView snapshots={history ?? []} />
                  )}
                </div>
              )}

              {noteError && (
                <div className="notice notice-error" style={{ marginBottom: '0.75rem' }}>
                  Could not create the note: {noteError}
                </div>
              )}
              {/* 🎯 Goal */}
              <div className="gap-summary-card">
            <p className="gap-summary-text">{r.summary.text || 'Gap analysis complete.'}</p>
            <div className="gap-summary-meta">
              {r.goal && <span className="badge badge-info">🎯 {r.goal}</span>}
              {r.summary.priorities.length > 0 && (
                <span className="gap-meta">Top priorities: {r.summary.priorities.join(', ')}</span>
              )}
            </div>
          </div>

          {/* Domain breakdown */}
          {r.domain_breakdown.length > 0 && (
            <div className="gap-block">
              <h3>🗺️ Domain Readiness</h3>
              <div className="gap-domain-grid">
                {r.domain_breakdown.map((d) => (
                  <div key={d.domain} className="gap-domain-card" style={{ borderTop: `3px solid ${statusColor(d.status)}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                      <strong style={{ fontSize: '0.82rem' }}>{d.domain}</strong>
                      <span
                        className="gap-domain-status"
                        style={{ color: statusColor(d.status), background: `${statusColor(d.status)}1a` }}
                      >
                        {d.status}
                      </span>
                    </div>
                    {(() => {
                      const strong = d.strong ?? [];
                      const developing = d.developing ?? [];
                      const gapsN = d.gaps ?? [];
                      return (
                        <>
                          <div className="gap-meta" style={{ marginTop: '0.35rem' }}>
                            {strong.length > 0 && <span>✓ {strong.length} strong</span>}
                            {developing.length > 0 && <span> · developing {developing.length}</span>}
                            {gapsN.length > 0 && <span> · {gapsN.length} gap{gapsN.length === 1 ? '' : 's'}</span>}
                          </div>
                          {gapsN.length > 0 && (
                            <div className="gap-chip-wrap" style={{ marginTop: '0.4rem' }}>
                              {gapsN.slice(0, 5).map((n) => (
                                <span key={n} className="gap-prereq-chip" style={{ color: 'var(--danger)' }}>{n}</span>
                              ))}
                              {gapsN.length > 5 && <span className="gap-hint">+{gapsN.length - 5} more</span>}
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 📚 Learn This Next */}
          {result.next && (
            <div className="gap-block">
              <h3>📚 Learn This Next</h3>
              <p className="gap-hint">The single highest-value concept for this goal right now.</p>
              <GapCard
                gap={result.next}
                open
                onToggle={() => {}}
                onOpenDoc={openDoc}
                onCreateNote={(g) => createNote(g, result.goal)}
                noteBusy={noteBusy === result.next?.name}
              />
            </div>
          )}

          {/* 🧠 Strengths */}
          <div className="gap-block">
            <h3>🧠 Your Strengths ({r.strengths.length})</h3>
            {r.strengths.length > 0 ? (
              <div className="gap-strength-chips">
                {r.strengths.map((s) => (
                  <span key={s.name} className="gap-strength-chip" title={s.why ?? ''}>
                    ✓ {s.name} <LevelBadge level={s.level} />
                  </span>
                ))}
              </div>
            ) : (
              <p className="gap-hint">No strong evidence yet for this goal — start from the first path phase.</p>
            )}
          </div>

          {/* ⚠️ Knowledge gaps */}
          <div className="gap-block">
            <h3>⚠️ Knowledge Gaps ({r.gaps.length})</h3>
            <p className="gap-hint">
              Ranked by importance × how little evidence you have. Open a gap for why, prerequisites, learn/practice steps, and linked notes.
            </p>
            <div className="gap-list">
              {r.gaps.filter((g) => g.name !== r.next?.name).slice(0, 20).map((g) => (
                <GapCard
                  key={g.name}
                  gap={g}
                  open={openGap === g.name}
                  onToggle={() => setOpenGap(openGap === g.name ? null : g.name)}
                  onOpenDoc={openDoc}
                  onCreateNote={(g) => createNote(g, result.goal)}
                  noteBusy={noteBusy === g.name}
                />
              ))}
            </div>
          </div>

          {/* 🛣️ Learning path */}
          {r.path.length > 0 && (
            <div className="gap-block">
              <h3>🛣️ Recommended Learning Path</h3>
              <p className="gap-hint">
                Prerequisite-first across all of the goal's domains. Each step links to the Second Brain
                documents that mention it, and can draft a study note.
              </p>
              <GapPathPhaseView
                phases={r.path}
                onOpenDoc={openDoc}
                onCreateNote={(item) => createNote(item, result.goal)}
                noteBusy={noteBusy}
              />
            </div>
          )}

              <p className="gap-meta">
                Evidence coverage: {r.coverage.known} of {r.coverage.total} target concepts have evidence
                ({Math.round(r.coverage.percent)}%). Percentages are secondary — the path above tells you what to do next.
              </p>
            </div>
            );
          })()}
        </>
      )}
    </div>
  );
};
