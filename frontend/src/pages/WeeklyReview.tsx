import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints, type WeeklyReviewResponse } from '../services/api';

const styles = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', alignItems: 'start' },
  card: { padding: '1rem 1.15rem' },
  title: { fontSize: '0.85rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.45rem' },
  sub: { fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
  subBlock: { fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.05em', marginTop: '0.8rem' },
  row: {
    display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.45rem 0.15rem',
    borderBottom: '1px solid var(--border)', fontSize: '0.8rem',
  },
  empty: { fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.4rem 0' },
  chip: {
    fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    padding: '0.1rem 0.45rem', borderRadius: 999, flexShrink: 0,
  },
  stat: { display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.45rem 0.15rem', fontSize: '0.8rem' },
  insight: { fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '0.2rem 0' },
  listTitle: { fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', margin: '0.6rem 0 0.2rem' },
};

function renderMarkdownish(text: string) {
  // Minimal renderer for the reflection markdown (headings + bullets).
  return text.split('\n').map((line, i) => {
    if (line.startsWith('# ')) return <h3 key={i} style={{ fontSize: '0.95rem', margin: '0.4rem 0' }}>{line.slice(2)}</h3>;
    if (line.startsWith('## ')) return <div key={i} style={styles.listTitle}>{line.slice(3).toUpperCase()}</div>;
    if (line.startsWith('- ')) return <div key={i} style={styles.insight}>• {line.slice(2)}</div>;
    if (!line.trim()) return <div key={i} style={{ height: '0.35rem' }} />;
    return <div key={i} style={styles.insight}>{line}</div>;
  });
}

export const WeeklyReview = () => {
  const [data, setData] = useState<WeeklyReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await endpoints.kb.weeklyReview.overview());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const generate = async (regenerate: boolean) => {
    setGenerating(true);
    setNotice(null);
    try {
      const res = await endpoints.kb.weeklyReview.generateReflection(regenerate);
      setNotice(regenerate ? 'Reflection regenerated ✓' : 'Reflection generated ✓');
      void load();
      return res;
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Generation failed');
      return null;
    } finally {
      setGenerating(false);
    }
  };

  const confirmGoal = async (title: string, subjectId: number) => {
    setNotice(null);
    try {
      await endpoints.kb.weeklyReview.confirmGoal({ title, subject_id: subjectId });
      setNotice(`Goal “${title}” confirmed ✓`);
      void load();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not confirm goal');
    }
  };

  if (loading && !data) {
    return (
      <div>
        <Header title="Weekly Review" />
        <p style={{ padding: '2rem', color: 'var(--text-secondary)' }}>Preparing your weekly review…</p>
      </div>
    );
  }

  const activity = data?.activity;
  const reflection = data?.reflection;
  const insights = reflection?.insights;

  return (
    <div>
      <Header title="🗓️ Weekly Review" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        {data?.week_label ?? ''} — a guided end-of-week ritual: review what you did, reflect on how it went, then plan next week.
      </p>

      {notice && <div className="notice notice-success" style={{ marginBottom: '0.75rem' }}>{notice}</div>}

      <div style={styles.grid}>
        {/* ── 1. Week at a glance ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>📊 1 · This week</h3>
          <p style={styles.sub}>What you did</p>
          <div style={styles.stat}><span>📥</span><span style={{ flex: 1 }}>Notes captured</span><strong>{activity?.captures_count ?? 0}</strong></div>
          <div style={styles.stat}><span>🎯</span><span style={{ flex: 1 }}>Sessions completed</span><strong>{activity?.sessions_done ?? 0}</strong></div>
          <div style={styles.stat}><span>⏱️</span><span style={{ flex: 1 }}>Focus minutes</span><strong>{activity?.focus_minutes ?? 0}</strong></div>
          <div style={styles.stat}><span>🍅</span><span style={{ flex: 1 }}>Pomodoros</span><strong>{activity?.pomodoro_count ?? 0}</strong></div>
          <div style={styles.stat}><span>🧩</span><span style={{ flex: 1 }}>Learning events</span><strong>{activity?.learning_events ?? 0}</strong></div>

          <div style={styles.subBlock}>CAPTURES</div>
          {activity?.captures.length === 0 ? (
            <p style={styles.empty}>No notes captured this week.</p>
          ) : (
            activity?.captures.slice(0, 8).map((c) => (
              <Link key={c.id} to={`/knowledge-base?doc=${c.id}`} style={{ ...styles.row, textDecoration: 'none', color: 'inherit' }}>
                <span>📄</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</span>
              </Link>
            ))
          )}
        </div>

        {/* ── 2. Reflection ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>🧠 2 · Reflection</h3>
          <p style={styles.sub}>Generated from your learning events</p>

          <div style={{ display: 'flex', gap: '0.5rem', margin: '0.75rem 0', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-sm btn-primary" disabled={generating} onClick={() => void generate(false)}>
              {generating ? 'Generating…' : reflection ? '↻ Regenerate' : '✨ Generate reflection'}
            </button>
          </div>

          {!reflection && <p style={styles.empty}>No reflection yet — generate one from this week's learning events.</p>}

          {reflection && (
            <div style={{ marginTop: '0.5rem' }}>
              {insights && (
                <div style={{ marginBottom: '0.5rem' }}>
                  {(insights.worked ?? []).length > 0 && (
                    <>
                      <div style={styles.listTitle}>✅ WORKED</div>
                      {insights.worked.map((w) => <div key={w} style={styles.insight}>• {w}</div>)}
                    </>
                  )}
                  {(insights.struggled ?? []).length > 0 && (
                    <>
                      <div style={styles.listTitle}>⚠️ STRUGGLED</div>
                      {insights.struggled.map((s) => <div key={s} style={styles.insight}>• {s}</div>)}
                    </>
                  )}
                </div>
              )}
              <div style={{ ...styles.subBlock, marginTop: '0.2rem' }}>FULL REFLECTION</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{renderMarkdownish(reflection.content ?? '')}</div>
            </div>
          )}
        </div>

        {/* ── 3. Goals & next week ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>🎯 3 · Goals & next week</h3>
          <p style={styles.sub}>Auto-proposed from your subjects</p>

          {data?.derived_goals.length === 0 ? (
            <p style={styles.empty}>No new term goals to propose — all active subjects already have one.</p>
          ) : (
            data?.derived_goals.map((g) => (
              <div key={g.subject_id} style={styles.row}>
                <span>🏆</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.title}</span>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={() => void confirmGoal(g.title, g.subject_id)}
                >
                  ✓ Confirm
                </button>
              </div>
            ))
          )}

          <div style={styles.subBlock}>ACTIVE GOALS ({data?.goals.length ?? 0})</div>
          {data?.goals.length === 0 ? (
            <p style={styles.empty}>No goals yet.</p>
          ) : (
            data?.goals.map((g) => (
              <div key={g.id} style={styles.row}>
                <span>🎯</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.title}</span>
                <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{g.progress_percentage}%</span>
              </div>
            ))
          )}

          <div style={styles.subBlock}>WEAK TOPICS</div>
          {data?.weak_topics.length === 0 ? (
            <p style={styles.empty}>No weak or unknown topics — nice work.</p>
          ) : (
            data?.weak_topics.map((w) => (
              <Link key={w.topic_id} to={`/subjects/${w.subject_id ?? ''}`} style={{ ...styles.row, textDecoration: 'none', color: 'inherit' }}>
                <span>🕳️</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.topic_name}</span>
                <span style={{ ...styles.chip, background: 'var(--danger-muted)', color: 'var(--danger)' }}>{w.classification}</span>
              </Link>
            ))
          )}

          <div style={styles.subBlock}>WEEKLY QUESTS</div>
          {data?.weekly_quests.length === 0 ? (
            <p style={styles.empty}>No weekly quests — run the weekly reset to create them.</p>
          ) : (
            data?.weekly_quests.map((q) => (
              <div key={q.id} style={styles.row}>
                <span>⚔️</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.title}</span>
                <span style={{ ...styles.chip, background: 'var(--success-muted)', color: 'var(--success)' }}>{q.status}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '1.25rem' }}>
        <Link className="btn btn-sm btn-ghost" to="/today">📅 Back to Today</Link>
        <Link className="btn btn-sm btn-ghost" to="/goals">🎯 Goals</Link>
        <Link className="btn btn-sm btn-ghost" to="/analytics">📈 Analytics</Link>
      </div>
    </div>
  );
};
