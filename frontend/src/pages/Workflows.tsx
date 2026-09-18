import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type {
  FocusBoard,
  HealthAudit,
  HealthAuditDuplicate,
  KbMissingNoteSuggestion,
  KbOutdatedNote,
  KbQualityItem,
} from '../services/api';

const styles = {
  card: { padding: '1rem 1.15rem', marginBottom: '0.9rem' },
  sub: { fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
  row: {
    display: 'flex', alignItems: 'center', gap: '0.55rem', padding: '0.45rem 0.15rem',
    borderBottom: '1px solid var(--border)', fontSize: '0.8rem',
  },
  chip: {
    fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    padding: '0.1rem 0.45rem', borderRadius: 999, flexShrink: 0,
  },
  empty: { fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.4rem 0' },
};

const fmtPct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)}%`);

const REASON_LABEL: Record<string, string> = {
  stale: 'STALE',
  contradiction: 'CONTRADICTS',
  material_changed: 'MATERIAL CHANGED',
};

const REASON_COLOR: Record<string, { color: string; bg: string }> = {
  stale: { color: 'var(--warning)', bg: 'var(--warning-muted)' },
  contradiction: { color: 'var(--danger)', bg: 'var(--danger-muted)' },
  material_changed: { color: 'var(--info)', bg: 'var(--info-muted)' },
};

export const Workflows = () => {
  // Vault Health Audit state
  const [audit, setAudit] = useState<HealthAudit | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);
  const [auditNotice, setAuditNotice] = useState<string | null>(null);

  // Focus/Readiness Loop state
  const [focus, setFocus] = useState<FocusBoard | null>(null);
  const [focusBusy, setFocusBusy] = useState<number | null>(null);
  const [focusNotice, setFocusNotice] = useState<string | null>(null);

  const loadAudit = useCallback(async () => {
    try {
      const res = await endpoints.kb.healthAudit.audit();
      setAudit(res);
    } catch {
      setAudit(null);
    }
  }, []);

  const loadFocus = useCallback(async () => {
    try {
      const res = await endpoints.kb.focus.board();
      setFocus(res);
    } catch {
      setFocus(null);
    }
  }, []);

  useEffect(() => { void loadAudit(); }, [loadAudit]);
  useEffect(() => { void loadFocus(); }, [loadFocus]);

  const rescan = async () => {
    setAuditBusy(true);
    setAuditNotice(null);
    try {
      const res = await endpoints.kb.healthAudit.rescan();
      setAuditNotice(`Re-scanned the vault · health score ${res.health_score}/100 · ${res.created_outdated} new outdated-note flag(s).`);
      void loadAudit();
    } catch (e) {
      setAuditNotice(e instanceof Error ? e.message : 'Re-scan failed');
    } finally {
      setAuditBusy(false);
    }
  };

  const dismissMissing = async (s: KbMissingNoteSuggestion) => {
    try {
      await endpoints.kb.healthAudit.dismissMissing(s.id);
      void loadAudit();
    } catch (e) {
      setAuditNotice(e instanceof Error ? e.message : 'Could not dismiss');
    }
  };

  const resolveOutdated = async (n: KbOutdatedNote, action: 'updated' | 'archived' | 'dismissed') => {
    try {
      await endpoints.kb.healthAudit.resolveOutdated(n.id, action);
      void loadAudit();
    } catch (e) {
      setAuditNotice(e instanceof Error ? e.message : 'Could not resolve');
    }
  };

  const archiveDuplicate = async (d: HealthAuditDuplicate) => {
    try {
      await endpoints.kb.healthAudit.archiveDuplicate(d.document_id);
      void loadAudit();
    } catch (e) {
      setAuditNotice(e instanceof Error ? e.message : 'Could not archive');
    }
  };

  const startFocus = async (topicId: number) => {
    setFocusBusy(topicId);
    setFocusNotice(null);
    try {
      const res = await endpoints.kb.focus.start(topicId);
      setFocusNotice(
        `⏱ Started a ${res.session.duration_mins}-minute session: ${res.session.practice_task}. Finish it in the Pomodoro view to log it.`,
      );
      // Defect #64 fix: re-fetch the focus board after starting so the
      // active-state toggle reflects without a page reload.
      void loadFocus();
    } catch (e) {
      setFocusNotice(e instanceof Error ? e.message : 'Could not start session');
    } finally {
      setFocusBusy(null);
    }
  };

  const missingRow = (s: KbMissingNoteSuggestion) => (
    <div key={s.id} style={styles.row}>
      <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>NOTE GAP</span>
      <span style={{ flex: 1, minWidth: 0 }}>
        <strong>{String(s.concept)}</strong>
        <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)' }}>{s.reason}</span>
      </span>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void dismissMissing(s)}>Dismiss</button>
    </div>
  );

  const outdatedRow = (n: KbOutdatedNote) => {
    const st = REASON_COLOR[n.reason] ?? REASON_COLOR.stale;
    return (
      <div key={n.id} style={styles.row}>
        <span style={{ ...styles.chip, background: st.bg, color: st.color }}>{REASON_LABEL[n.reason] ?? n.reason}</span>
        <span style={{ flex: 1, minWidth: 0 }}>{n.title}</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void resolveOutdated(n, 'dismissed')}>Dismiss</button>
      </div>
    );
  };

  const duplicateRow = (d: HealthAuditDuplicate) => (
    <div key={`${d.document_id}-${d.duplicate_of_id}`} style={styles.row}>
      <span style={{ ...styles.chip, background: 'var(--warning-muted)', color: 'var(--warning)' }}>DUP</span>
      <span style={{ flex: 1, minWidth: 0 }}>
        <strong>{d.title}</strong> <span style={{ color: 'var(--text-muted)' }}>≈ {Math.round((d.similarity ?? 0) * 100)}% of</span> {d.duplicate_of_title}
      </span>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void archiveDuplicate(d)}>Archive</button>
    </div>
  );

  const qualityRow = (q: KbQualityItem) => (
    <div key={q.document_id} style={styles.row}>
      <span style={{ ...styles.chip, background: q.score < 40 ? 'var(--danger-muted)' : 'var(--warning-muted)', color: q.score < 40 ? 'var(--danger)' : 'var(--warning)' }}>
        {q.score}/100
      </span>
      <span style={{ flex: 1, minWidth: 0 }}>{q.title}</span>
      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{q.doc_type}</span>
    </div>
  );

  return (
    <div>
      <Header title="⚙️ Workflows" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Read-mostly flows that reuse your existing data — opening this page never calls the AI and never re-analyzes anything.
        Every action below is an explicit button press.
      </p>

      {auditNotice && <div className="notice notice-success" style={{ marginBottom: '0.75rem' }}>{auditNotice}</div>}
      {focusNotice && <div className="notice notice-success" style={{ marginBottom: '0.75rem' }}>{focusNotice}</div>}

      {/* ── Focus / Readiness Loop ── */}
      <div className="card" style={{ ...styles.card, borderLeft: '3px solid var(--accent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
          <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🎯 What should I study right now?</h3>
          <span style={{ flex: 1 }} />
          {focus && focus.at_risk_count > 0 && (
            <span style={{ ...styles.chip, background: 'var(--danger-muted)', color: 'var(--danger)' }}>
              {focus.at_risk_count} subject(s) at risk
            </span>
          )}
          {focus && focus.exam_approaching.length > 0 && (
            <span style={{ ...styles.chip, background: 'var(--warning-muted)', color: 'var(--warning)' }}>
              {focus.exam_approaching.length} exam(s) within 14 days
            </span>
          )}
        </div>
        <p style={styles.sub}>Exam-aware readiness — forecast + next-action, deterministic</p>

        {focus?.recommendations.length === 0 ? (
          <p style={styles.empty}>
            No recommendations yet — import a syllabus and confirm its topics to get a study-now board.
          </p>
        ) : (
          (focus?.recommendations ?? []).map((r) => (
            <div key={r.topic_id} style={styles.row}>
              <span style={{ ...styles.chip, background: r.ready ? 'var(--success-muted)' : 'var(--warning-muted)', color: r.ready ? 'var(--success)' : 'var(--warning)' }}>
                {r.ready ? 'READY' : 'BLOCKED'}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <strong>{r.topic_name}</strong>
                {r.subject_readiness && (
                  <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    readiness {fmtPct(r.subject_readiness.readiness)}
                    {r.subject_readiness.exam_days_until != null && <> · exam in {r.subject_readiness.exam_days_until}d</>}
                    {r.subject_readiness.at_risk && <> · ⚠ at risk</>}
                  </span>
                )}
                {r.reasons && (
                  <span style={{ display: 'block', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                    weak {fmtPct(r.reasons.weakness)} · due {fmtPct(r.reasons.due_reviews)} · gap {fmtPct(r.reasons.concept_gaps)} · exam {fmtPct(r.reasons.exam_proximity)}
                  </span>
                )}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={focusBusy === r.topic_id}
                onClick={() => void startFocus(r.topic_id)}
              >
                {focusBusy === r.topic_id ? 'Starting…' : '▶ Study now'}
              </button>
            </div>
          ))
        )}
      </div>

      {/* ── Vault Health Audit ── */}
      <div className="card" style={{ ...styles.card, borderLeft: '3px solid var(--info)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
          <h3 style={{ fontSize: '0.9rem', margin: 0 }}>🩺 Vault Health Audit</h3>
          <span style={{ flex: 1 }} />
          {audit?.health.score != null && (
            <span
              style={{
                ...styles.chip,
                background: (audit.health.score ?? 0) >= 70 ? 'var(--success-muted)' : (audit.health.score ?? 0) >= 45 ? 'var(--warning-muted)' : 'var(--danger-muted)',
                color: (audit.health.score ?? 0) >= 70 ? 'var(--success)' : (audit.health.score ?? 0) >= 45 ? 'var(--warning)' : 'var(--danger)',
              }}
            >
              health {audit.health.score}/100
            </span>
          )}
          <button type="button" className="btn btn-ghost btn-sm" disabled={auditBusy} onClick={() => void rescan()}>
            {auditBusy ? 'Scanning…' : '🔄 Re-scan'}
          </button>
        </div>
        <p style={styles.sub}>Aggregates existing signals — nothing is re-analyzed on load</p>

        {audit && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            <span>📄 <strong>{audit.health.document_count}</strong> docs</span>
            <span>· 🔗 <strong>{audit.health.edge_count}</strong> links</span>
            {audit.health.dead_links > 0 && <span>· <strong style={{ color: 'var(--danger)' }}>{audit.health.dead_links} broken links</strong></span>}
            {audit.health.orphans > 0 && <span>· <strong style={{ color: 'var(--warning)' }}>{audit.health.orphans} orphaned</strong></span>}
            {audit.health.stale_notes > 0 && <span>· <strong style={{ color: 'var(--warning)' }}>{audit.health.stale_notes} stale notes</strong></span>}
            {audit.health.unindexed_files > 0 && <span>· <strong style={{ color: 'var(--warning)' }}>{audit.health.unindexed_files} unindexed files</strong></span>}
          </div>
        )}

        <h4 style={{ fontSize: '0.8rem', margin: '0.7rem 0 0.2rem' }}>📝 Missing notes ({audit?.counts.missing_notes ?? 0})</h4>
        {!audit?.sections.missing_notes.length ? <p style={styles.empty}>Nothing missing — every studied concept has a note.</p> : audit.sections.missing_notes.map(missingRow)}

        <h4 style={{ fontSize: '0.8rem', margin: '0.7rem 0 0.2rem' }}>🔄 Outdated notes ({audit?.counts.outdated_notes ?? 0})</h4>
        {!audit?.sections.outdated_notes.length ? <p style={styles.empty}>No outdated-note flags open.</p> : audit.sections.outdated_notes.map(outdatedRow)}

        <h4 style={{ fontSize: '0.8rem', margin: '0.7rem 0 0.2rem' }}>👯 Near-duplicates ({audit?.counts.duplicates ?? 0})</h4>
        {!audit?.sections.duplicates.length ? <p style={styles.empty}>No duplicate documents recorded.</p> : audit.sections.duplicates.map(duplicateRow)}

        <h4 style={{ fontSize: '0.8rem', margin: '0.7rem 0 0.2rem' }}>📉 Low-quality notes ({audit?.counts.low_quality ?? 0})</h4>
        {!audit?.sections.low_quality.length ? <p style={styles.empty}>No low-quality notes — the vault looks healthy.</p> : audit.sections.low_quality.map(qualityRow)}
      </div>
    </div>
  );
};
