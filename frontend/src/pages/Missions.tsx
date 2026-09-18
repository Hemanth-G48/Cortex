import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { RpgLayout } from '../components/rpg/RpgLayout';
import { RpgCard } from '../components/rpg/RpgCard';
import { RpgBadge } from '../components/rpg/RpgBadge';
import { RpgTabs } from '../components/rpg/RpgTabs';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import type { Mission, MissionTask, QuestCentreBoard } from '../services/api';

const sidebar = (
  <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    <Link to="/character" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>👤</span> Profile</Link>
    <Link to="/quests" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>⚔️</span> Quests</Link>
    <Link to="/missions" className="sidebar-link active" style={{ textDecoration: 'none', color: 'inherit' }}><span>🎯</span> Missions</Link>
    <Link to="/rewards" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>🎁</span> Rewards</Link>
    <Link to="/rpg-dashboard" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}><span>📊</span> Dashboard</Link>
  </nav>
);

type TabId = 'all' | 'in-progress' | 'not-started' | 'completed';

export const Missions = () => {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [tasks, setTasks] = useState<Record<number, MissionTask[]>>({});
  // Defect #88 fix: authoritative mission counts from the server board.
  const [board, setBoard] = useState<QuestCentreBoard | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', xp_reward: 50 });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.missions.list()
      .then(setMissions)
      .catch(() => setError('Could not load missions — is the backend running?'))
      .finally(() => setLoading(false));
    endpoints.questCentre.board().then(setBoard).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    missions.forEach((m) => {
      const missionId = m.id;
      // Defect #24 fix: typed endpoints object instead of inline api.get.
      endpoints.missions.listTasks(missionId).then((ts) => {
        setTasks((prev) => ({ ...prev, [missionId]: ts }));
      }).catch(() => {});
    });
  }, [missions]);

  // Defect #82 fix: mission creation from this page.
  const handleCreate = async () => {
    if (!form.title.trim()) return;
    try {
      await endpoints.missions.create({
        title: form.title.trim(),
        description: form.description || null,
        xp_reward: Number(form.xp_reward) || 50,
      });
      setForm({ title: '', description: '', xp_reward: 50 });
      setShowCreate(false);
      load();
    } catch {
      setError('Could not create mission');
    }
  };

  const handleDelete = (id: number) => {
    if (!confirmDelete('this mission')) return;
    endpoints.missions.delete(id).then(load).catch(() => setError('Could not delete mission'));
  };

  const filtered = missions.filter((m) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'in-progress') return m.status === 'In progress';
    if (activeTab === 'not-started') return m.status === 'Not started';
    if (activeTab === 'completed') return m.status === 'Completed';
    return true;
  });

  // Prefer the authoritative server counts; fall back to the loaded page.
  const byStatus = board?.missions.by_status;
  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: 'all', label: 'All', count: board?.missions.total ?? missions.length },
    { id: 'in-progress', label: 'In Progress', count: byStatus?.['In progress'] ?? missions.filter((m) => m.status === 'In progress').length },
    { id: 'not-started', label: 'Not Started', count: byStatus?.['Not started'] ?? missions.filter((m) => m.status === 'Not started').length },
    { id: 'completed', label: 'Completed', count: byStatus?.['Completed'] ?? missions.filter((m) => m.status === 'Completed').length },
  ];

  return (
    <RpgLayout sidebar={sidebar}>
      <div>
        <h2 className="pixel-text" style={{ color: '#ff9800', fontSize: '1rem', marginBottom: '16px' }}>
          🎯 Mission Center
        </h2>
        <button
          type="button"
          className="rpg-btn"
          style={{ marginBottom: '12px', cursor: 'pointer' }}
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? '− Cancel' : '+ New Mission'}
        </button>

        {showCreate && (
          <RpgCard style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input placeholder="Mission title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
              <input placeholder="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              <div style={{ display: 'flex', gap: '8px' }}>
                <input type="number" placeholder="XP reward" value={form.xp_reward} onChange={(e) => setForm({ ...form, xp_reward: Number(e.target.value) })} style={{ width: 120 }} />
                <button type="button" className="rpg-btn" onClick={() => void handleCreate()} disabled={!form.title.trim()}>Create</button>
              </div>
            </div>
          </RpgCard>
        )}

        <RpgTabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as TabId)} />

        {/* Defect #86/#88 fix: explicit loading/error feedback. */}
        {loading && <div className="rpg-empty" style={{ marginTop: '16px' }}><div className="rpg-empty-text">Loading missions…</div></div>}
        {error && (
          <div className="rpg-empty" style={{ marginTop: '16px' }}>
            <div className="rpg-empty-icon">⚠</div>
            <div className="rpg-empty-text">{error}</div>
            <button type="button" className="rpg-btn" onClick={load}>Retry</button>
          </div>
        )}
        {!loading && !error && filtered.length === 0 ? (
          <div className="rpg-empty" style={{ marginTop: '16px' }}>
            <div className="rpg-empty-icon">🎯</div>
            <div className="rpg-empty-text">No missions found.</div>
          </div>
        ) : (
          <div className="card-grid" style={{ marginTop: '16px' }}>
            {filtered.map((m) => {
              const missionTasks = tasks[m.id] || [];
              const doneCount = missionTasks.filter((t) => t.completed).length;
              const pct = missionTasks.length > 0 ? Math.round((doneCount / missionTasks.length) * 100) : 0;
              return (
                <RpgCard key={m.id} style={{ borderLeft: `3px solid ${m.status === 'Completed' ? 'var(--rpg-accent-green)' : m.status === 'In progress' ? 'var(--rpg-accent-orange)' : 'var(--rpg-border)'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '0.9rem' }}>{m.title}</h3>
                    <RpgBadge variant="gold">+{m.xp_reward} XP</RpgBadge>
                  </div>
                  {m.description && <p style={{ fontSize: '0.78rem', color: 'var(--rpg-text-secondary)', marginBottom: '8px' }}>{m.description}</p>}
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
                    <RpgBadge variant={m.status === 'Completed' ? 'green' : m.status === 'In progress' ? 'orange' : 'red'}>{m.status}</RpgBadge>
                    {m.priority && <RpgBadge variant={m.priority === 'High' ? 'red' : m.priority === 'Medium' ? 'orange' : 'green'}>{m.priority}</RpgBadge>}
                  </div>
                  {missionTasks.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <div className="rpg-progress-bar" style={{ height: '4px' }}>
                        <div className="rpg-progress-fill-green" style={{ width: `${pct}%` }} />
                      </div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--rpg-text-muted)', marginTop: '4px' }}>
                        {doneCount}/{missionTasks.length} subtasks
                      </div>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                    <button onClick={() => handleDelete(m.id)} style={{ background: 'none', border: 'none', color: 'var(--habit-red)', cursor: 'pointer', fontSize: '0.7rem' }}>Delete</button>
                  </div>
                </RpgCard>
              );
            })}
          </div>
        )}
      </div>
    </RpgLayout>
  );
};
