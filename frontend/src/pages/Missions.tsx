import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RpgLayout } from '../components/rpg/RpgLayout';
import { RpgCard } from '../components/rpg/RpgCard';
import { RpgBadge } from '../components/rpg/RpgBadge';
import { RpgTabs } from '../components/rpg/RpgTabs';
import { endpoints, api } from '../services/api';
import type { Mission, MissionTask } from '../services/api';

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
  const [activeTab, setActiveTab] = useState<TabId>('all');

  useEffect(() => {
    endpoints.missions.list().then(setMissions).catch(() => {});
  }, []);

  useEffect(() => {
    missions.forEach((m) => {
      const missionId = m.id;
      const url = `/missions/${missionId}/tasks`;
      const endpoint = { list: () => api.get<MissionTask[]>(url) };
      endpoint.list().then((ts) => {
        setTasks((prev) => ({ ...prev, [missionId]: ts }));
      }).catch(() => {});
    });
  }, [missions]);

  const filtered = missions.filter((m) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'in-progress') return m.status === 'In progress';
    if (activeTab === 'not-started') return m.status === 'Not started';
    if (activeTab === 'completed') return m.status === 'Completed';
    return true;
  });

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: 'all', label: 'All', count: missions.length },
    { id: 'in-progress', label: 'In Progress', count: missions.filter((m) => m.status === 'In progress').length },
    { id: 'not-started', label: 'Not Started', count: missions.filter((m) => m.status === 'Not started').length },
    { id: 'completed', label: 'Completed', count: missions.filter((m) => m.status === 'Completed').length },
  ];

  return (
    <RpgLayout sidebar={sidebar}>
      <div>
        <h2 className="pixel-text" style={{ color: '#ff9800', fontSize: '1rem', marginBottom: '16px' }}>
          🎯 Mission Center
        </h2>
        <RpgTabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as TabId)} />
        {filtered.length === 0 ? (
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
                </RpgCard>
              );
            })}
          </div>
        )}
      </div>
    </RpgLayout>
  );
};
