import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { endpoints } from '../services/api';
import type {
  KbConceptGap,
  KbGapItem,
  KbHealth,
  KbMemoryItem,
  KbMissingNoteSuggestion,
  KbOutdatedNote,
} from '../services/api';

function scoreColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

interface SignalCardProps {
  icon: string;
  title: string;
  count: number;
  detail: string;
  hint: string;
}

const SignalCard = ({ icon, title, count, detail, hint }: SignalCardProps) => (
  <div className="card" style={{ padding: '0.9rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <span style={{ fontSize: '1.15rem' }}>{icon}</span>
      <strong style={{ fontSize: '0.82rem', flex: 1 }}>{title}</strong>
      <span
        style={{
          fontSize: '0.8rem',
          fontWeight: 800,
          color: count === 0 ? '#10b981' : '#f59e0b',
          background: count === 0 ? '#10b9811a' : '#f59e0b1a',
          borderRadius: 999,
          padding: '0.1rem 0.55rem',
        }}
      >
        {count}
      </span>
    </div>
    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', minHeight: '2.2em' }}>{detail}</div>
    <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)' }}>{hint}</div>
  </div>
);

const strengthColor = (s: number) => (s >= 0.6 ? '#10b981' : s >= 0.3 ? '#f59e0b' : '#ef4444');

export const KbInsights = () => {
  const navigate = useNavigate();
  const [health, setHealth] = useState<KbHealth | null>(null);
  const [gaps, setGaps] = useState<KbGapItem[]>([]);
  const [gapThreshold, setGapThreshold] = useState(0.2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Phase 8 (Ideas 72, 77, 78, 79) ──
  const [conceptGaps, setConceptGaps] = useState<KbConceptGap[]>([]);
  const [suggestions, setSuggestions] = useState<KbMissingNoteSuggestion[]>([]);
  const [outdated, setOutdated] = useState<KbOutdatedNote[]>([]);
  const [memory, setMemory] = useState<KbMemoryItem[]>([]);
  const [p8Busy, setP8Busy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, g] = await Promise.all([endpoints.kb.health(), endpoints.kb.gaps.all()]);
      setHealth(h);
      setGaps(g.gaps ?? []);
      setGapThreshold(g.threshold ?? 0.2);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPhase8 = useCallback(async () => {
    try {
      const [cg, su, od, mem] = await Promise.all([
        endpoints.kb.gaps.concepts().catch(() => ({ items: [] as KbConceptGap[] })),
        endpoints.kb.missingNotes.list().catch(() => ({ items: [] as KbMissingNoteSuggestion[] })),
        endpoints.kb.outdated.review().catch(() => ({ items: [] as KbOutdatedNote[] })),
        endpoints.kb.memory.get(50).catch(() => ({ items: [] as KbMemoryItem[] })),
      ]);
      setConceptGaps(cg.items);
      setSuggestions(su.items);
      setOutdated(od.items);
      setMemory(mem.items);
    } catch {
      /* personalization endpoints may 404 on older backends */
    }
  }, []);

  useEffect(() => {
    void load();
    void loadPhase8();
  }, [load, loadPhase8]);

  const openDoc = (docId: number) => navigate(`/knowledge-base?doc=${docId}`);

  const scanOutdated = async () => {
    setP8Busy(true);
    try {
      await endpoints.kb.outdated.scan();
      await loadPhase8();
    } finally {
      setP8Busy(false);
    }
  };

  const resolveOutdated = async (noteId: number, action: 'updated' | 'archived' | 'dismissed') => {
    await endpoints.kb.outdated.resolve(noteId, action);
    await loadPhase8();
  };

  const acceptSuggestion = async (id: number) => {
    const res = await endpoints.kb.missingNotes.accept(id);
    await loadPhase8();
    if (res.document_id) openDoc(res.document_id);
  };

  const dismissSuggestion = async (id: number) => {
    await endpoints.kb.missingNotes.dismiss(id);
    await loadPhase8();
  };

  const generateSuggestions = async () => {
    setP8Busy(true);
    try {
      await endpoints.kb.missingNotes.generate();
      await loadPhase8();
    } finally {
      setP8Busy(false);
    }
  };

  if (loading) return <div className="page-section"><Header title="Knowledge Health" /><p style={{ padding: '2rem', color: 'var(--text-secondary)' }}>Analyzing vault…</p></div>;

  return (
    <div className="page-section">
      <Header title="Knowledge Health" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Signals over your vault: orphans, dead links, stale notes, unindexed files, coverage gaps, concept-level gaps, missing notes, and outdated notes.
      </p>

      {error && (
        <div style={{ padding: '0.6rem 1rem', borderRadius: 8, marginBottom: '0.75rem', background: '#ef444422', color: '#ef4444', fontSize: '0.85rem' }}>
          {error}
        </div>
      )}

      {!health ? (
        <EmptyState icon="🩺" title="No health data" message="Ingest a few documents first — health is computed per user." />
      ) : (
        <>
          {/* ── Score hero ── */}
          <div
            className="card"
            style={{
              padding: '1.25rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '1.25rem',
              flexWrap: 'wrap',
              background: 'linear-gradient(135deg, var(--bg-card), var(--bg-hover))',
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.6rem', fontWeight: 900, lineHeight: 1, color: scoreColor(health.score) }}>
                {Math.round(health.score)}
              </div>
              <div style={{ fontSize: '0.66rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginTop: '0.3rem' }}>
                / 100 health
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ height: 10, borderRadius: 5, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${Math.max(0, Math.min(100, health.score))}%`,
                    background: scoreColor(health.score),
                    transition: 'width 0.5s ease',
                  }}
                />
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.4rem' }}>
                {health.document_count} documents · {health.edge_count} edges
              </div>
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => { void load(); void loadPhase8(); }}>
              ↻ Refresh
            </button>
          </div>

          {/* ── Signal cards ── */}
          <h3 style={{ fontSize: '0.9rem', margin: '0.25rem 0 0.5rem' }}>Signals</h3>
          <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
            <SignalCard
              icon="🏝️"
              title="Orphans"
              count={health.signals.orphans.count}
              detail={health.signals.orphans.document_ids.length ? `#${health.signals.orphans.document_ids.slice(0, 6).join(', #')}${health.signals.orphans.document_ids.length > 6 ? '…' : ''}` : 'None — every doc is linked or tagged'}
              hint="Isolated notes: no edges and no tags. Merge or delete."
            />
            <SignalCard
              icon="💀"
              title="Dead links"
              count={health.signals.dead_links.count}
              detail={health.signals.dead_links.count ? `${health.signals.dead_links.count} WIKILINK/BACKLINK edge(s) point to missing docs` : 'All links resolve'}
              hint="Edges whose target document no longer exists."
            />
            <SignalCard
              icon="🕸️"
              title="Stale notes"
              count={health.signals.stale_notes.count}
              detail={health.signals.stale_notes.document_ids.length ? `#${health.signals.stale_notes.document_ids.slice(0, 6).join(', #')}${health.signals.stale_notes.document_ids.length > 6 ? '…' : ''}` : 'Nothing stale'}
              hint="Unvisited for a long time — refresh or archive."
            />
            <SignalCard
              icon="🧩"
              title="Unindexed files"
              count={health.signals.unindexed_files.count}
              detail={health.signals.unindexed_files.count ? `${health.signals.unindexed_files.documents[0]?.missing.join(', ') ?? ''}${health.signals.unindexed_files.count > 1 ? ` (+${health.signals.unindexed_files.count - 1} more)` : ''}` : 'Everything embedded, chunked and tagged'}
              hint="Missing chunks/embeddings/tags — reindex."
            />
            <SignalCard
              icon="🕳️"
              title="Coverage gaps"
              count={gaps.length}
              detail={gaps.length ? gaps.slice(0, 3).map((g) => `${g.topic} (${Math.round(g.coverage * 100)}%)`).join(', ') : 'No gaps below threshold'}
              hint={`Topics below ${Math.round(gapThreshold * 100)}% coverage — capture notes.`}
            />
          </div>

          {/* ── Gap list ── */}
          <h3 style={{ fontSize: '0.9rem', margin: '1.25rem 0 0.5rem' }}>🕳️ Missing knowledge</h3>
          {gaps.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>No gaps — all topics clear the coverage threshold.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {gaps.map((g) => (
                <div key={g.topic} className="card" style={{ padding: '0.7rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '0.8rem', minWidth: 120 }}>{g.topic}</strong>
                  <div style={{ flex: 1, minWidth: 140, height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.min(100, g.coverage * 100)}%`, background: '#f59e0b' }} />
                  </div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    {Math.round(g.coverage * 100)}% covered
                  </span>
                  <button type="button" className="btn btn-sm btn-primary" onClick={() => navigate('/knowledge-base')}>
                    + Capture note
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* ── Phase 8: concept-level gaps (Idea 72) ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1.5rem 0 0.5rem' }}>
            <h3 style={{ fontSize: '0.9rem', margin: 0 }}>💡 Concept-level gaps ({conceptGaps.length})</h3>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              quiz errors + retrieval misses + mastery strength
            </span>
          </div>
          {conceptGaps.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              No concept gaps yet — answer quiz questions wrong or search for something missing to surface them here.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {conceptGaps.map((g) => (
                <div key={g.concept_id} className="card" style={{ padding: '0.7rem 1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '0.8rem', minWidth: 130 }}>{g.concept}</strong>
                    <div style={{ flex: 1, minWidth: 120, height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(100, g.score * 100)}%`, background: scoreColor(100 - g.score * 100) }} />
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      {g.evidence.quiz_errors} errors · {g.evidence.retrieval_misses} misses · strength {Math.round(g.evidence.strength * 100)}%
                    </span>
                    {g.sources.length > 0 && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--accent)', cursor: 'pointer' }} onClick={() => openDoc(g.sources[0].document_id)}>
                        📄 {g.sources[0].title}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Phase 8: missing-note suggestions (Idea 77) ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1.5rem 0 0.5rem', flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: '0.9rem', margin: 0 }}>📝 Missing-note suggestions ({suggestions.length})</h3>
            <button type="button" className="btn btn-sm btn-ghost" disabled={p8Busy} onClick={() => void generateSuggestions()}>
              ✨ Suggest
            </button>
          </div>
          {suggestions.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Nothing to suggest — you study topics/concepts that have no note covering them.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {suggestions.map((s) => (
                <div key={s.id} className="card" style={{ padding: '0.7rem 1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 180 }}>
                      <strong style={{ fontSize: '0.8rem' }}>{String(s.concept)}</strong>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>{s.reason}</div>
                      {s.outline.length > 0 && (
                        <div style={{ fontSize: '0.66rem', color: 'var(--text-muted)', marginTop: '0.25rem', fontFamily: 'monospace' }}>
                          {s.outline.slice(0, 3).join(' · ')}{s.outline.length > 3 ? ' …' : ''}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      <button type="button" className="btn btn-sm btn-primary" onClick={() => void acceptSuggestion(s.id)}>
                        + Create draft note
                      </button>
                      <button type="button" className="btn btn-sm btn-ghost" onClick={() => void dismissSuggestion(s.id)}>
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Phase 8: outdated review queue (Idea 78) ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', margin: '1.5rem 0 0.5rem', flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: '0.9rem', margin: 0 }}>⏳ Outdated notes ({outdated.length})</h3>
            <button type="button" className="btn btn-sm btn-ghost" disabled={p8Busy} onClick={() => void scanOutdated()}>
              ▶ Scan
            </button>
          </div>
          {outdated.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              No open flags — run a scan to detect stale notes, changed materials, and contradictions.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {outdated.map((n) => (
                <div key={n.id} className="card" style={{ padding: '0.7rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <span style={{ flex: 1, minWidth: 160, cursor: 'pointer', fontSize: '0.8rem' }} onClick={() => openDoc(n.document_id)}>
                    <strong>{n.title}</strong>
                  </span>
                  <span
                    style={{
                      fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em',
                      padding: '0.15rem 0.5rem', borderRadius: 999,
                      color: n.reason === 'contradiction' ? '#ef4444' : n.reason === 'material_changed' ? '#f59e0b' : '#8b5cf6',
                      background: `${n.reason === 'contradiction' ? '#ef4444' : n.reason === 'material_changed' ? '#f59e0b' : '#8b5cf6'}1a`,
                    }}
                  >
                    {n.reason.replace('_', ' ')}
                  </span>
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => void resolveOutdated(n.id, 'updated')}>✓ Updated</button>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => void resolveOutdated(n.id, 'archived')}>🗄 Archive</button>
                    <button type="button" className="btn btn-sm btn-ghost" onClick={() => void resolveOutdated(n.id, 'dismissed')}>✕ Dismiss</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Phase 8: learning memory (Idea 79) — read-only strength bars ── */}
          <h3 style={{ fontSize: '0.9rem', margin: '1.5rem 0 0.5rem' }}>🧠 Learning memory ({memory.length})</h3>
          {memory.length === 0 ? (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              No memory yet — quiz answers, tutor turns, reviews and note views build it up over time.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              {memory.slice(0, 12).map((m) => (
                <div key={m.concept_id} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.75rem' }}>
                  <span style={{ minWidth: 150 }}>{m.concept}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--muted, #e5e7eb)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${m.strength * 100}%`, background: strengthColor(m.strength), transition: 'width 0.4s' }} />
                  </div>
                  <span style={{ color: 'var(--text-muted)', width: 34, textAlign: 'right' }}>{Math.round(m.strength * 100)}%</span>
                </div>
              ))}
            </div>
          )}

          {/* ── Quick fix actions per signal (phrase 70) ── */}
          {health.signals.orphans.document_ids.length > 0 && (
            <div style={{ marginTop: '1rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              Fix: review orphan docs —{' '}
              {health.signals.orphans.document_ids.slice(0, 5).map((id) => (
                <button key={id} type="button" className="btn btn-sm btn-ghost" style={{ marginRight: '0.3rem' }} onClick={() => openDoc(id)}>
                  #{id}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};
