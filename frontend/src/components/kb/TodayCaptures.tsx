import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { endpoints, type KbDailyNotes } from '../../services/api';

const styles = {
  section: { marginTop: '1.5rem' },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: '0.6rem',
  },
  title: { fontSize: '0.95rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' },
  sub: { fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' as const, letterSpacing: '0.05em' },
  group: { fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', margin: '0.6rem 0 0.25rem' },
  row: {
    display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0.6rem',
    borderRadius: 8, fontSize: '0.8rem', color: 'var(--text-primary)', textDecoration: 'none',
    transition: 'background 0.12s',
  },
  chip: {
    fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    padding: '0.1rem 0.45rem', borderRadius: 999, flexShrink: 0,
  },
  empty: { fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.3rem 0' },
};

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export const TodayCaptures = () => {
  const [data, setData] = useState<KbDailyNotes | null>(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const load = () => {
    Promise.all([
      endpoints.kb.dailyNotes.today().catch(() => null),
      endpoints.dailyLogs.list().catch(() => []),
      endpoints.journal.list().catch(() => []),
    ]).then(([notes, , journal]) => {
      if (!mountedRef.current) return;
      const base = notes ?? { date: new Date().toISOString().slice(0, 10), documents: [], schedule: [], journal: [] };
      // Merge chronologically-newer journal entries created after the morning
      // snapshot so the widget reflects the live day. DB entries carry a date;
      // daily-note journal items have no timestamp, so they keep their order.
      const merged: KbDailyNotes = {
        ...base,
        documents: base.documents,
        schedule: base.schedule,
        journal: [
          ...base.journal,
          ...journal.map((e) => ({ id: e.id, mood: e.mood ?? null, content: e.content, tags: e.tags ?? null })),
        ].slice(-20),
      };
      setData(merged);
    }).catch(() => { if (mountedRef.current) setData(null); })
      .finally(() => { if (mountedRef.current) setLoading(false); });
  };

  useEffect(() => {
    load();
    const tick = setInterval(load, 60_000);
    return () => { mountedRef.current = false; window.clearInterval(tick); };
  }, [load]);

  if (loading && !data) return null;
  if (!data) return null;

  const dayName = DAYS[new Date(data.date).getDay()] ?? '';

  return (
    <div style={styles.section}>
      <div style={styles.header}>
        <h3 style={styles.title}>📥 Captured today</h3>
        <Link to={`/knowledge-base?doc=${data.documents[0]?.id ?? ''}`} style={styles.sub}>
          {data.date} · {dayName}
        </Link>
      </div>

      <div style={styles.group}>VAULT NOTES ({data.documents.length})</div>
      {data.documents.length === 0 ? (
        <p style={styles.empty}>No vault documents captured today yet.</p>
      ) : (
        data.documents.map((d) => (
          <Link key={d.id} to={`/knowledge-base?doc=${d.id}`} style={styles.row}>
            <span>📄</span>
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title}</span>
            {d.quality_score !== null && (
              <span style={{ ...styles.chip, background: 'var(--info-muted)', color: 'var(--info)' }}>
                {d.quality_score}/100
              </span>
            )}
          </Link>
        ))
      )}

      {data.schedule.length > 0 && (
        <>
          <div style={styles.group}>SCHEDULE ({data.schedule.length})</div>
          {data.schedule.map((s) => (
            <div key={s.id} style={styles.row}>
              <span style={{ ...styles.chip, background: s.done ? 'var(--success-muted)' : 'var(--warning-muted)', color: s.done ? 'var(--success)' : 'var(--warning)' }}>
                {s.time_range}
              </span>
              <span style={{ flex: 1, textDecoration: s.done ? 'line-through' : 'none', opacity: s.done ? 0.6 : 1 }}>
                {s.activity}
              </span>
            </div>
          ))}
        </>
      )}

      {data.journal.length > 0 && (
        <>
          <div style={styles.group}>JOURNAL ({data.journal.length})</div>
          {data.journal.map((j) => (
            <div key={j.id} style={styles.row}>
              <span>📔</span>
              <span style={{ color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {j.content}
              </span>
              {j.mood && <span style={styles.chip}>{j.mood}</span>}
            </div>
          ))}
        </>
      )}
    </div>
  );
};
