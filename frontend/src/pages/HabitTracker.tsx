import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Habit } from '../services/api';

export const HabitTracker = () => {
  const [habits, setHabits] = useState<Habit[]>([]);

  const load = () => endpoints.habits.list().then(setHabits).catch(() => {});

  useEffect(() => { load(); }, []);

  const handleLog = (habitId: number) => {
    endpoints.habits.logToday(habitId).then(load);
  };

  const handleDelete = (id: number) => {
    endpoints.habits.delete(id).then(load);
  };

  const sorted = [...habits].sort((a, b) => b.current_streak - a.current_streak);
  const totalStreaks = habits.reduce((s, h) => s + h.current_streak, 0);

  return (
    <div>
      <Header title="Habit Tracker" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total Habits</div><div className="value">{habits.length}</div></div>
        <div className="stat-tile"><div className="label">Total Streaks</div><div className="value">{totalStreaks}</div></div>
        <div className="stat-tile"><div className="label">Top Streak</div><div className="value">{sorted[0]?.longest_streak ?? 0}d</div></div>
      </div>
      <div className="card-grid">
        {sorted.map((h) => (
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
