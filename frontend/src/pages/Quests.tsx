import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Quest } from '../services/api';

export const Quests = () => {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => { endpoints.quests.list(filter || undefined).then(setQuests).catch(() => {}); }, [filter]);

  const totalXp = quests.filter((q) => q.status === 'Completed').reduce((s, q) => s + q.xp_reward, 0);

  return (
    <div>
      <Header title="Quest Center" />
      <div className="flex gap-2 mb-2 flex-wrap">
        {(['Work', 'Fitness', 'Personal', 'Learning', 'Social', 'Health'] as const).map((cat) => (
          <button key={cat} className={`btn btn-sm ${filter === cat ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setFilter(cat)}>
            {cat}
          </button>
        ))}
      </div>
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Active Quests</div><div className="value">{quests.filter((q) => q.status !== 'Completed').length}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{quests.filter((q) => q.status === 'Completed').length}</div></div>
        <div className="stat-tile"><div className="label">Total XP Earned</div><div className="value">{totalXp}</div></div>
      </div>
      <div className="card-grid">
        {quests.map((q) => (
          <div className="card" key={q.id} style={{ borderLeft: `3px solid ${q.status === 'Completed' ? 'var(--success)' : q.status === 'In progress' ? 'var(--warning)' : 'var(--border)'}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <h3>{q.title}</h3>
              <span className="badge badge-warning">+{q.xp_reward} XP</span>
            </div>
            {q.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{q.description}</p>}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span className={`badge badge-${q.status === 'Completed' ? 'success' : q.status === 'In progress' ? 'warning' : 'info'}`}>{q.status}</span>
              {q.due_date && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Due: {q.due_date}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
