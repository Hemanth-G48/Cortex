import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints, type MicroSession, type TodayOverview } from '../services/api';

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
};

export const Today = () => {
  const [data, setData] = useState<TodayOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<MicroSession | null>(null);
  const [startingId, setStartingId] = useState<number | null>(null);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await endpoints.kb.today.overview());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load today');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const startSession = async (a: { topic_id: number; session_length_mins?: number }) => {
    setStartingId(a.topic_id);
    setSessionNotice(null);
    try {
      const res = await endpoints.kb.sessions.start(a.topic_id, a.session_length_mins);
      setSession(res.session);
      setSessionNotice('Micro-session started — pick a pomodoro or complete when done.');
    } catch (e) {
      setSessionNotice(e instanceof Error ? e.message : 'Could not start session');
    } finally {
      setStartingId(null);
    }
  };

  const launchPomodoro = async (s: MicroSession) => {
    setSessionBusy(true);
    setSessionNotice(null);
    try {
      const res = await endpoints.kb.sessions.pomodoro(s.id);
      setSessionNotice(`Pomodoro launched (${res.duration_minutes}m) — ${res.task_description ?? ''}`.trim());
    } catch (e) {
      setSessionNotice(e instanceof Error ? e.message : 'Could not launch pomodoro');
    } finally {
      setSessionBusy(false);
    }
  };

  const completeSession = async (s: MicroSession) => {
    setSessionBusy(true);
    setSessionNotice(null);
    try {
      await endpoints.kb.sessions.complete(s.id);
      // Defect #61: completing a micro-session moves XP + vault mastery, so
      // re-read those exact sources (character sheet, leaderboard, mastery) and
      // report the new totals in the same banner.
      const [character, board, mastery] = await Promise.all([
        endpoints.characters.get(1).catch(() => null),
        endpoints.leaderboard.list(20).catch(() => null),
        endpoints.kb.mastery().catch(() => null),
      ]);
      const bits: string[] = [];
      if (character) bits.push(`Level ${character.level} · ${character.xp} XP`);
      if (mastery && mastery.topics_total > 0) bits.push(`vault mastery ${mastery.score_pct}%`);
      if (board?.me) bits.push(`rank ${board.me.rank}`);
      setSessionNotice(
        `Session completed — XP and mastery logged 🎉${bits.length ? ` (${bits.join(' · ')})` : ''}`,
      );
      // Close the running panel and refresh so today's focus stats reflect the completion.
      setSession(null);
      void load();
    } catch (e) {
      setSessionNotice(e instanceof Error ? e.message : 'Could not complete session');
    } finally {
      setSessionBusy(false);
    }
  };

  if (loading && !data) {
    return (
      <div>
        <Header title="Today" />
        <p style={{ padding: '2rem', color: 'var(--text-secondary)' }}>Building your day…</p>
      </div>
    );
  }

  const morning = data?.morning;
  const evening = data?.evening;
  const dayName = data ? `${data.day_name}, ${new Date(data.date).toLocaleDateString()}` : '';

  return (
    <div>
      <Header title="📅 Today" />
      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        {dayName} — plan in the morning, focus, then close the day. Everything below is live from your vault, schedule and study plan.
      </p>

      {error && <div className="notice notice-error" style={{ marginBottom: '1rem' }}>{error}</div>}

      <div style={styles.grid}>
        {/* ── Morning review ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>🌅 Morning review</h3>
          <p style={styles.sub}>What's due & what to study first</p>

          <div style={styles.subBlock}>DUE REVIEWS ({morning?.reviews_due.length ?? 0})</div>
          {morning?.reviews_due.length === 0 ? (
            <p style={styles.empty}>Nothing due — revision queue is clear 🎉</p>
          ) : (
            morning?.reviews_due.map((r) => (
              <div key={r.schedule_id} style={styles.row}>
                <span>🔁</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.topic_name}</span>
                <span style={{ ...styles.chip, background: 'var(--warning-muted)', color: 'var(--warning)' }}>due {r.due_date}</span>
              </div>
            ))
          )}

          <div style={styles.subBlock}>NEXT ACTION</div>
          {morning?.next_actions.length === 0 ? (
            <p style={styles.empty}>No study topics yet — import a syllabus or scan your vault.</p>
          ) : (
            morning?.next_actions.map((a) => (
              <div key={a.topic_id} style={styles.row}>
                <span>🎯</span>
                <Link to={`/subjects/${a.subject_id ?? ''}`} style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--accent)', textDecoration: 'none' }}>
                  {a.topic_name}
                </Link>
                <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{a.session_length_mins}m</span>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  data-testid={`start-session-${a.topic_id}`}
                  disabled={startingId === a.topic_id || session?.topic_id === a.topic_id}
                  onClick={() => void startSession(a)}
                >
                  {startingId === a.topic_id ? 'Starting…' : session?.topic_id === a.topic_id ? 'Running' : '▶ Start'}
                </button>
              </div>
            ))
          )}

          {sessionNotice && (
            <div
              style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.5rem', padding: '0.35rem 0.6rem', borderRadius: 8, background: 'var(--warning-muted)' }}
              data-testid="session-notice"
            >
              {sessionNotice}
            </div>
          )}

          {session && (
            <div
              style={{
                marginTop: '0.75rem', padding: '0.7rem 0.85rem', borderRadius: 10,
                background: 'var(--accent-muted)', border: '1px solid var(--accent)',
              }}
              data-testid="launched-session"
            >
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.3rem' }}>
                🎧 Session running
              </div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem' }}>{session.topic_name ?? 'Untitled session'}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                {session.practice_task ?? 'Focus on this topic.'} · {session.duration_mins ?? 25}m
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-sm btn-primary" disabled={sessionBusy} onClick={() => void launchPomodoro(session)}>
                  {sessionBusy ? 'Launching…' : '🍅 Launch pomodoro'}
                </button>
                <button type="button" className="btn btn-sm btn-ghost" disabled={sessionBusy} onClick={() => void completeSession(session)}>
                  ✓ Complete
                </button>
                <button type="button" className="btn btn-sm btn-ghost" onClick={() => setSession(null)}>
                  ✕ Close
                </button>
              </div>
            </div>
          )}

          <div style={styles.subBlock}>DEADLINES</div>
          {morning?.deadlines.length === 0 ? (
            <p style={styles.empty}>No upcoming deadlines.</p>
          ) : (
            morning?.deadlines.map((d) => (
              <div key={`${d.kind}-${d.id}`} style={styles.row}>
                <span>{d.kind === 'exam' ? '📋' : d.kind === 'assignment' ? '📝' : '✅'}</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title}</span>
                <span style={{ ...styles.chip, background: 'var(--danger-muted)', color: 'var(--danger)' }}>{d.due_date ?? '—'}</span>
              </div>
            ))
          )}
        </div>

        {/* ── Schedule today ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>🗓️ Schedule today</h3>
          <p style={styles.sub}>Your day blocks</p>
          {morning?.schedule.length === 0 ? (
            <p style={styles.empty}>No schedule blocks for today. Add them on the Schedule page or materialize due reviews.</p>
          ) : (
            morning?.schedule.map((s) => (
              <div key={s.id} style={styles.row}>
                <span style={{ ...styles.chip, background: s.done ? 'var(--success-muted)' : 'var(--accent-muted)', color: s.done ? 'var(--success)' : 'var(--accent)' }}>
                  {s.time_range}
                </span>
                <span style={{ flex: 1, textDecoration: s.done ? 'line-through' : 'none', opacity: s.done ? 0.6 : 1 }}>
                  {s.activity}
                </span>
              </div>
            ))
          )}

          <div style={{ ...styles.sub, marginTop: '0.9rem' }}>CAPTURED TODAY ({morning?.captured_documents.length ?? 0})</div>
          {morning?.captured_documents.length === 0 ? (
            <p style={styles.empty}>Nothing captured in the vault today yet.</p>
          ) : (
            morning?.captured_documents.map((d) => (
              <Link key={d.id} to={`/knowledge-base?doc=${d.id}`} style={{ ...styles.row, textDecoration: 'none', color: 'inherit' }}>
                <span>📄</span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title}</span>
                {d.quality_score !== null && (
                  <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>{d.quality_score}/100</span>
                )}
              </Link>
            ))
          )}
        </div>

        {/* ── Evening close ── */}
        <div className="card" style={styles.card}>
          <h3 style={styles.title}>🌙 Evening review</h3>
          <p style={styles.sub}>Close the day</p>

          <div style={styles.stat}>
            <span>⏱️</span>
            <span style={{ flex: 1 }}>Focus time</span>
            <strong>{evening?.focus_minutes ?? 0} min</strong>
          </div>
          <div style={styles.stat}>
            <span>🍅</span>
            <span style={{ flex: 1 }}>Pomodoros</span>
            <strong>{evening?.pomodoros.length ?? 0}</strong>
          </div>
          <div style={styles.stat}>
            <span>📥</span>
            <span style={{ flex: 1 }}>Notes captured</span>
            <strong>{data?.captured_today_count ?? 0}</strong>
          </div>

          <div style={styles.subBlock}>POMODOROS</div>
          {evening?.pomodoros.length === 0 ? (
            <p style={styles.empty}>No pomodoros today — run one from the Pomodoro page.</p>
          ) : (
            evening?.pomodoros.map((p) => (
              <div key={p.id} style={styles.row}>
                <span style={{ ...styles.chip, background: p.completed ? 'var(--success-muted)' : 'var(--warning-muted)', color: p.completed ? 'var(--success)' : 'var(--warning)' }}>
                  {p.completed ? 'done' : 'running'}
                </span>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.task_description ?? `Pomodoro ${p.duration_minutes ?? 25}m`}</span>
              </div>
            ))
          )}

          <div style={styles.subBlock}>JOURNAL</div>
          {evening?.journal.length === 0 ? (
            <p style={styles.empty}>No journal entry for today.</p>
          ) : (
            evening?.journal.map((j) => (
              <div key={j.id} style={styles.row}>
                <span>📔</span>
                <span style={{ color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.content}</span>
                {j.mood && <span style={styles.chip}>{j.mood}</span>}
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '1.25rem' }}>
        <Link className="btn btn-sm btn-ghost" to="/pomodoro">⏱️ Start a pomodoro</Link>
        <Link className="btn btn-sm btn-ghost" to="/flashcard-review">📥 Review queue</Link>
        <Link className="btn btn-sm btn-ghost" to="/weekly-review">🗓️ Weekly review</Link>
        {/* Folders organize the vault — notes inside a course folder already
            belong to it. New-note triage is no longer part of the workflow. */}
      </div>
    </div>
  );
};
