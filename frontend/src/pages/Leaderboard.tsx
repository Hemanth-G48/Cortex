import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { EmptyState } from '../components/shared/EmptyState';
import { endpoints, type KbMastery, type LeaderboardEntry, type LeaderboardResponse } from '../services/api';

const CLASS_ICONS: Record<string, string> = {
  Wizard: '🧙',
  Knight: '🛡️',
  Rogue: '🗡️',
  Mage: '🔮',
  Ranger: '🏹',
  Cleric: '✨',
  Warrior: '⚔️',
};

const classIcon = (name?: string | null) => CLASS_ICONS[name ?? ''] ?? '👤';

const MEDALS = ['🥇', '🥈', '🥉'];

const styles = {
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.9rem',
    padding: '0.7rem 0.9rem',
    borderRadius: 12,
    marginBottom: '0.45rem',
  },
  rank: { width: 34, fontWeight: 800, fontSize: '0.85rem', color: 'var(--text-muted)', textAlign: 'center' as const },
  name: { fontWeight: 600, fontSize: '0.85rem', color: 'var(--text-primary)' },
  meta: { fontSize: '0.68rem', color: 'var(--text-secondary)' },
  xp: { marginLeft: 'auto', fontWeight: 800, fontSize: '0.85rem', color: 'var(--accent)' },
};

export const Leaderboard = () => {
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(20);
  // Defect #76: XP alone hides vault work — show the mastery breakdown too.
  const [mastery, setMastery] = useState<KbMastery | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [board, vault] = await Promise.all([
        endpoints.leaderboard.list(limit),
        endpoints.kb.mastery().catch(() => null),
      ]);
      setData(board);
      setMastery(vault);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    void load();
  }, [load]);

  const me = data?.me;

  return (
    <div className="fade-in" style={{ maxWidth: 680 }}>
      <Header title="Leaderboard" />

      {me && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--accent)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.4rem' }}>🏆</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                You're <span style={{ color: 'var(--accent)' }}>#{me.rank}</span> of {me.total_users} students
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Top {me.percentile}% · {me.total_xp.toLocaleString()} XP
              </div>
              {/* Defect #76: vault mastery weighting beside the XP total. */}
              {mastery && mastery.topics_total > 0 && (
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                  Vault mastery <strong style={{ color: 'var(--text-primary)' }}>{mastery.score_pct}%</strong>
                  {' '}({mastery.topics_mastered}/{mastery.topics_total} topics strong · {mastery.hours_logged}h logged)
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.9rem' }}>
        {[10, 20, 50].map((n) => (
          <button
            key={n}
            type="button"
            className="btn btn-sm"
            onClick={() => setLimit(n)}
            style={limit === n ? { color: 'var(--accent)', borderColor: 'var(--accent)' } : undefined}
          >
            Top {n}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Loading leaderboard…</p>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon="🏆"
          title="No XP yet"
          message="Earn XP by completing quests, habits, and study sessions — then check back to see where you rank."
        />
      ) : (
        data.items.map((e: LeaderboardEntry) => (
          <div
            key={e.user_id}
            className="card"
            style={{
              ...styles.row,
              borderColor: e.me ? 'var(--accent)' : undefined,
              background: e.me ? 'var(--accent-muted)' : undefined,
            }}
          >
            <div style={styles.rank}>{MEDALS[e.rank - 1] ?? `#${e.rank}`}</div>
            <div style={{ fontSize: '1.2rem' }}>{classIcon(e.avatar_class)}</div>
            <div style={{ minWidth: 0 }}>
              <div style={styles.name}>
                {e.name}
                {e.me && <span style={{ fontSize: '0.62rem', color: 'var(--accent)', marginLeft: '0.35rem' }}>(you)</span>}
              </div>
              <div style={styles.meta}>Lv {e.level} · 🔥 {e.current_streak} day streak</div>
            </div>
            <div style={styles.xp}>{e.total_xp.toLocaleString()} XP</div>
          </div>
        ))
      )}
    </div>
  );
};
