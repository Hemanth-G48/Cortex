import { useEffect, useMemo, useState, useCallback } from 'react';
import { NavLink } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { EmptyState } from '../components/shared/EmptyState';
import { SkeletonCard } from '../components/shared/Skeleton';
import type { Habit, TodayOverview } from '../services/api';

/**
 * Broadcast a habit-data change so other pages (VaultDashboard heatmap)
 * can refresh without a full reload (audit defects #12/#77).
 */
export const notifyHabitChange = () => {
  window.dispatchEvent(new CustomEvent('habits:changed'));
};

/** Subscribe to habit-data changes from other pages. */
export const onHabitChange = (cb: () => void): (() => void) => {
  const handler = () => cb();
  window.addEventListener('habits:changed', handler);
  return () => window.removeEventListener('habits:changed', handler);
};

export const HabitTracker = () => {
  const [habits, setHabits] = useState<Habit[]>([]);
  // Defect #45: today's vault focus (next-action engine output) boosts the
  // habits that align with what the Second Brain says to work on now.
  const [todayOverview, setTodayOverview] = useState<TodayOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [frequency, setFrequency] = useState('daily');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.habits.list()
      .then(setHabits)
      .catch(() => setError('Could not load habits — is the backend running?'))
      .finally(() => setLoading(false));
    endpoints.kb.today
      .overview()
      .then(setTodayOverview)
      .catch(() => setTodayOverview(null));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Defect #12 fix: keep in sync with changes made on the Vault dashboard.
  useEffect(() => onHabitChange(load), [load]);

  const handleLog = (habitId: number) => {
    endpoints.habits.logToday(habitId).then(() => {
      load();
      // Defect #77 fix: tell the Vault dashboard heatmap about the new log.
      notifyHabitChange();
    });
  };

  const handleDelete = (id: number) => {
    if (confirmDelete('this habit')) {
      endpoints.habits.delete(id).then(() => {
        load();
        notifyHabitChange();
      });
    }
  };

  // Defect #13 fix: habit creation from this page.
  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      await endpoints.habits.create({ name: name.trim(), description: description || null, frequency });
      setName('');
      setDescription('');
      setFrequency('daily');
      setShowCreate(false);
      load();
      notifyHabitChange();
    } catch {
      setError('Could not create habit');
    }
  };

  // Defect #45: order by alignment with today's vault focus topics first, then
  // by streak. Focus terms come from the live next-action engine
  // (GET /api/kb/today → morning.next_actions), not from a static list.
  const sorted = useMemo(() => {
    const focusTerms = new Set<string>();
    for (const action of todayOverview?.morning.next_actions ?? []) {
      for (const token of action.topic_name.toLowerCase().split(/[^a-z0-9]+/)) {
        if (token.length > 2) focusTerms.add(token);
      }
    }
    const boost = (habit: Habit) =>
      habit.name
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .filter((token) => token.length > 2 && focusTerms.has(token)).length;
    return [...habits].sort((a, b) => boost(b) - boost(a) || b.current_streak - a.current_streak);
  }, [habits, todayOverview]);
  const totalStreaks = habits.reduce((s, h) => s + h.current_streak, 0);

  return (
    <div>
      <Header title="Habit Tracker" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? '− Cancel' : '+ New Habit'}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Habit name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={frequency} onChange={(e) => setFrequency(e.target.value)} style={{ width: 'auto' }}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
            <button type="button" className="btn btn-primary" onClick={() => void handleCreate()} disabled={!name.trim()}>
              Create Habit
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total Habits</div><div className="value">{habits.length}</div></div>
        <div className="stat-tile"><div className="label">Total Streaks</div><div className="value">{totalStreaks}</div></div>
        <div className="stat-tile"><div className="label">Top Streak</div><div className="value">{sorted[0]?.longest_streak ?? 0}d</div></div>
      </div>
      <div className="card-grid">
        {loading ? (
          // Defect #14 fix: skeletons while loading.
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : habits.length === 0 ? (
          <EmptyState
            icon="🔥"
            title="No habits yet"
            message="Create your first habit to start building streaks."
            action={<button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>+ New Habit</button>}
          />
        ) : sorted.map((h) => (
          <div className="card" key={h.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
              <h3 style={{ marginBottom: '0.25rem' }}>{h.name}</h3>
              <button onClick={() => handleDelete(h.id)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
            </div>
            <NavLink to={`/habits/${h.id}/report`} style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>
              View Report →
            </NavLink>
            {h.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{h.description}</p>}
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
              <span className="badge badge-info">{h.frequency}</span>
              <span style={{ color: 'var(--accent)', fontWeight: 600 }}>🔥 {h.current_streak}d streak</span>
            </div>
            <div className="xp-bar" style={{ width: '100%', height: '6px' }}>
              <div className="xp-fill" style={{ width: `${Math.min(100, (h.current_streak / Math.max(h.longest_streak, 1)) * 100)}%`, height: '6px' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Best: {h.longest_streak}d</span>
              <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none' }} onClick={() => handleLog(h.id)}>✓ Log Today</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
