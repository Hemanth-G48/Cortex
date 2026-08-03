import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { RpgLayout } from '../components/rpg/RpgLayout';
import { RpgCard } from '../components/rpg/RpgCard';
import { RpgBadge } from '../components/rpg/RpgBadge';
import { RpgButton } from '../components/rpg/RpgButton';
import { WeeklyCalendar } from '../components/rpg/WeeklyCalendar';
import { endpoints } from '../services/api';
import type { Character, Quest, Mission, Reward, LifeArea, ScheduleEvent } from '../services/api';

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// ── Helpers ──

function relativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return 'unknown';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ── Sidebar ──

const sidebar = (
  <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    <Link to="/quest-centre" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>🏆</span> Quest Centre</Link>
    <Link to="/character" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>👤</span> Profile</Link>
    <Link to="/quests" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>⚔️</span> Quests</Link>
    <Link to="/missions" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>🎯</span> Missions</Link>
    <Link to="/rewards" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>🎁</span> Rewards</Link>
    <Link to="/rpg-dashboard" className="sidebar-link active" style={{ textDecoration: 'none', color: 'inherit' }}><span>📊</span> Dashboard</Link>
  </nav>
);

// ── Loading skeleton ──

function StatSkeleton() {
  return (
    <RpgCard>
      <div style={{ height: 14, width: '50%', background: '#2a2a2a', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ height: 24, width: '30%', background: '#2a2a2a', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ height: 8, width: '100%', background: '#2a2a2a', borderRadius: 4 }} />
    </RpgCard>
  );
}

function SectionSkeleton({ height = 120 }: { height?: number }) {
  return (
    <RpgCard>
      <div style={{ height, background: '#1a1a1a', borderRadius: 4 }} />
    </RpgCard>
  );
}

// ── Stats card ──

function StatCard({ label, value, color, suffix, progress, progressColor }: {
  label: string;
  value: string | number;
  color?: string;
  suffix?: string;
  progress?: number;
  progressColor?: string;
}) {
  return (
    <RpgCard>
      <div className="label" style={{ color: 'var(--rpg-text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: color || 'var(--rpg-text)' }}>
        {value}{suffix && <span style={{ fontSize: '0.8rem', color: '#888', marginLeft: 4 }}>{suffix}</span>}
      </div>
      {progress !== undefined && (
        <div className="rpg-progress-bar" style={{ marginTop: '8px' }}>
          <div
            className={`rpg-progress-fill-${progressColor || 'orange'}`}
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </RpgCard>
  );
}

// ── Activity types ──

interface Activity {
  id: string;
  type: 'quest_complete' | 'mission_complete' | 'reward_claimed';
  title: string;
  detail: string;
  timestamp: string | null;
  icon: string;
  color: string;
}

// ── Component ──

export const RPGDashboard = () => {
  const [char, setChar] = useState<Character | null>(null);
  const [quests, setQuests] = useState<Quest[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [areas, setAreas] = useState<LifeArea[]>([]);
  const [events, setEvents] = useState<ScheduleEvent[]>([]);
  const [claimedRewards, setClaimedRewards] = useState<Reward[]>([]);

  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setErrors([]);
    const errs: string[] = [];

    const safe = async <T,>(p: Promise<T>, name: string): Promise<T | null> => {
      try {
        return await p;
      } catch {
        errs.push(name);
        return null;
      }
    };

    const results = await Promise.all([
      safe(endpoints.characters.get(1), 'character'),
      safe(endpoints.quests.list(), 'quests'),
      safe(endpoints.missions.list(), 'missions'),
      safe(endpoints.lifeAreas.list(), 'life areas'),
      safe(endpoints.schedule.list(), 'schedule'),
      safe(endpoints.rewards.claimed(), 'claimed rewards'),
    ]);

    setChar(results[0]);
    setQuests(results[1] || []);
    setMissions(results[2] || []);
    setAreas(results[3] || []);
    setEvents(results[4] || []);
    setClaimedRewards(results[5] || []);
    if (errs.length) setErrors(errs);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Stats ──
  const xpPct = char ? Math.min(100, ((char.xp % 1000) / 1000) * 100) : 0;
  const activeQuests = quests.filter((q) => q.status !== 'Completed').length;
  const completedQuests = quests.filter((q) => q.status === 'Completed').length;
  const totalXp = quests.reduce((s, q) => s + (q.xp_reward || 0), 0);
  const completedMissions = missions.filter((m) => m.status === 'Completed').length;
  const xpToNext = char ? 1000 - (char.xp % 1000) : 1000;

  // ── Activity feed ──
  const activities: Activity[] = [
    ...quests
      .filter((q) => q.status === 'Completed')
      .map((q) => ({
        id: `q-${q.id}`,
        type: 'quest_complete' as const,
        title: q.title,
        detail: `+${q.xp_reward} XP`,
        timestamp: q.updated_at,
        icon: '⚔️',
        color: '#ff9800',
      })),
    ...missions
      .filter((m) => m.status === 'Completed')
      .map((m) => ({
        id: `m-${m.id}`,
        type: 'mission_complete' as const,
        title: m.title,
        detail: `+${m.xp_reward} XP`,
        timestamp: m.updated_at,
        icon: '🎯',
        color: '#4caf50',
      })),
    ...claimedRewards.map((r) => ({
      id: `r-${r.id}`,
      type: 'reward_claimed' as const,
      title: r.title,
      detail: `-${r.xp_cost} XP`,
      timestamp: r.claimed_date,
      icon: '🎁',
      color: '#ffd700',
    })),
  ].sort((a, b) => {
    if (!a.timestamp && !b.timestamp) return 0;
    if (!a.timestamp) return 1;
    if (!b.timestamp) return -1;
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  // ── Stat bars ──
  const statBars: { label: string; value: number; max: number; color: string }[] = char
    ? [
        { label: 'STR', value: char.strength, max: 20, color: '#e74c3c' },
        { label: 'AGI', value: char.agility, max: 20, color: '#2ecc71' },
        { label: 'INT', value: char.intelligence, max: 20, color: '#3498db' },
        { label: 'END', value: char.endurance, max: 20, color: '#9b59b6' },
      ]
    : [];

  if (loading) {
    return (
      <RpgLayout sidebar={sidebar}>
        <div>
          <h2 className="pixel-text" style={{ color: '#ff9800', fontSize: '1rem', marginBottom: '16px' }}>📊 RPG Dashboard</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            {[1, 2, 3, 4].map((i) => <StatSkeleton key={i} />)}
          </div>
          <SectionSkeleton height={200} />
        </div>
      </RpgLayout>
    );
  }

  return (
    <RpgLayout sidebar={sidebar}>
      <div>
        {/* ── Header ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 className="pixel-text" style={{ color: '#ff9800', fontSize: '1rem', margin: 0 }}>📊 RPG Dashboard</h2>
          <RpgButton variant="ghost" size="sm" onClick={fetchAll}>
            🔄 Refresh
          </RpgButton>
        </div>

        {/* Error banner */}
        {errors.length > 0 && (
          <RpgCard style={{ borderColor: '#e74c3c', marginBottom: 16, padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: '#e74c3c', fontFamily: 'monospace' }}>
                ⚠ Failed to load: {errors.join(', ')}
              </span>
              <RpgButton variant="ghost" size="sm" onClick={fetchAll}>Retry</RpgButton>
            </div>
          </RpgCard>
        )}

        {/* ── Stats Row ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          <StatCard label="Level" value={char?.level ?? '-'} color="#ffd700" />
          <StatCard label="XP Progress" value={char ? char.xp % 1000 : 0} suffix={`/ 1000`} progress={xpPct} />
          <StatCard label="Active Quests" value={activeQuests} />
          <StatCard label="Completed" value={`${completedQuests}Q / ${completedMissions}M`} color="#4caf50" progress={quests.length ? (completedQuests / quests.length) * 100 : 0} progressColor="green" />
          <StatCard label="Total XP Earned" value={totalXp} color="#ffd700" />
          <StatCard label="XP to Next Level" value={xpToNext} color="#888" />
        </div>

        {/* ── Character Stats ── */}
        <RpgCard style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: 0 }}>
              👤 {char?.name || 'Character'} — {char?.class_name || '—'}
            </h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: '0.7rem', color: '#ffd700', fontFamily: 'monospace', fontWeight: 600 }}>
                Lv.{char?.level ?? 1}
              </span>
              <span style={{ fontSize: '0.65rem', color: '#b0b0b0', fontFamily: 'monospace' }}>
                {char ? `${char.xp} / ${(char.level || 1) * 1000} XP` : ''}
              </span>
            </div>
          </div>
          <div className="rpg-progress-bar" style={{ marginBottom: 12, height: 10 }}>
            <div
              className="rpg-progress-fill-orange"
              style={{ width: `${xpPct}%`, height: '100%' }}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {statBars.map((s) => (
              <div key={s.label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6rem', marginBottom: 2 }}>
                  <span style={{ color: s.color, fontWeight: 600, fontFamily: 'monospace' }}>{s.label}</span>
                  <span style={{ color: '#888', fontFamily: 'monospace' }}>{s.value}/{s.max}</span>
                </div>
                <div className="rpg-progress-bar" style={{ height: 6 }}>
                  <div style={{
                    width: `${(s.value / s.max) * 100}%`,
                    height: '100%',
                    background: s.color,
                    borderRadius: 3,
                    transition: 'width 0.3s',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </RpgCard>

        {/* ── Weekly Calendar (full-width) ── */}
        <RpgCard style={{ marginBottom: 16, padding: 16 }}>
          <WeeklyCalendar />
        </RpgCard>

        {/* ── 2-col grid ── */}
        <div className="rpg-grid-2col">
          {/* Life Areas Progress */}
          <RpgCard>
            <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>LIFE AREAS</h3>
            {areas.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 16 }}>
                <span style={{ fontSize: '1.5rem' }}>🌱</span>
                <p style={{ fontSize: '0.75rem', color: 'var(--rpg-text-muted)', marginTop: 8 }}>
                  No life areas configured yet.
                </p>
                <Link to="/life-areas" className="rpg-btn rpg-btn-ghost" style={{ fontSize: '0.7rem', textDecoration: 'none' }}>
                  Set up life areas
                </Link>
              </div>
            ) : areas.map((a) => (
              <div key={a.id} style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '4px' }}>
                  <span>{a.name}</span>
                  <span style={{ color: 'var(--rpg-text-muted)' }}>{Math.round(a.progress_percent || 0)}%</span>
                </div>
                <div className="rpg-progress-bar">
                  <div className="rpg-progress-fill-green" style={{ width: `${a.progress_percent || 0}%` }} />
                </div>
              </div>
            ))}
          </RpgCard>

          {/* Weekly Schedule Mini */}
          <RpgCard>
            <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>WEEKLY SCHEDULE</h3>
            {events.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 16 }}>
                <span style={{ fontSize: '1.5rem' }}>📅</span>
                <p style={{ fontSize: '0.75rem', color: 'var(--rpg-text-muted)', marginTop: 8 }}>
                  No events scheduled this week.
                </p>
                <Link to="/schedule" className="rpg-btn rpg-btn-ghost" style={{ fontSize: '0.7rem', textDecoration: 'none' }}>
                  Add events
                </Link>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {events.slice(0, 8).map((e) => (
                  <div key={e.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.72rem' }}>
                    <span style={{
                      width: '24px', height: '24px', borderRadius: '4px',
                      background: e.color || '#2a2a2a', flexShrink: 0,
                    }} />
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.title}</span>
                    <RpgBadge variant="orange">{DAY_NAMES[e.day_of_week]}</RpgBadge>
                  </div>
                ))}
              </div>
            )}
          </RpgCard>

          {/* Activity Feed */}
          <RpgCard>
            <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>
              🔄 ACTIVITY FEED
            </h3>
            {activities.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 16 }}>
                <span style={{ fontSize: '1.5rem' }}>📭</span>
                <p style={{ fontSize: '0.75rem', color: 'var(--rpg-text-muted)', marginTop: 8 }}>
                  No activity yet. Complete a quest or mission to see it here!
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {activities.slice(0, 10).map((a) => (
                  <div
                    key={a.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 0',
                      borderBottom: '1px solid #2a2a2a',
                      fontSize: '0.72rem',
                    }}
                  >
                    <span style={{ fontSize: '0.85rem' }}>{a.icon}</span>
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.title}</div>
                      <div style={{ fontSize: '0.6rem', color: a.color, fontFamily: 'monospace' }}>{a.detail}</div>
                    </div>
                    <span style={{ fontSize: '0.6rem', color: '#666', fontFamily: 'monospace', flexShrink: 0 }}>
                      {relativeTime(a.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </RpgCard>

          {/* Quick Actions */}
          <RpgCard>
            <h3 className="pixel-text" style={{ fontSize: '0.75rem', color: '#ff9800', margin: '0 0 12px 0' }}>⚡ QUICK ACTIONS</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <Link to="/quest-centre" className="rpg-btn rpg-btn-orange" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>🏆 Quest Centre</Link>
              <Link to="/quests" className="rpg-btn rpg-btn-orange" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>⚔️ Quests</Link>
              <Link to="/rewards" className="rpg-btn rpg-btn-green" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>🎁 Rewards</Link>
              <Link to="/character" className="rpg-btn rpg-btn-ghost" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>👤 Profile</Link>
              <Link to="/missions" className="rpg-btn rpg-btn-ghost" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>🎯 Missions</Link>
              <Link to="/life-areas" className="rpg-btn rpg-btn-ghost" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>🌱 Life Areas</Link>
              <Link to="/schedule" className="rpg-btn rpg-btn-ghost" style={{ textDecoration: 'none', textAlign: 'center', fontSize: '0.72rem' }}>📅 Schedule</Link>
            </div>
          </RpgCard>
        </div>
      </div>
    </RpgLayout>
  );
};
