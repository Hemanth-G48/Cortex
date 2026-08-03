import { useState, useEffect } from 'react';
import { RpgTabs } from './RpgTabs';
import { MissionCard } from './MissionCard';
import { MissionCreateForm } from './MissionCreateForm';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Mission } from '../../services/api';

interface MissionCenterProps {
  onXpAwarded?: () => void;
}

const TABS = [
  { id: 'all', label: 'All' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'not_started', label: 'Not Started' },
  { id: 'completed', label: 'Completed' },
];

const INPUT_STYLE: React.CSSProperties = {
  width: '100%',
  backgroundColor: '#2a2a2a',
  border: '1px solid #3a3a3a',
  padding: '8px 10px',
  borderRadius: 6,
  color: '#fff',
  fontSize: 13,
  boxSizing: 'border-box',
  outline: 'none',
};

function filterMissions(missions: Mission[], tab: string): Mission[] {
  switch (tab) {
    case 'in_progress':
      return missions.filter((m) => m.status === 'In progress');
    case 'not_started':
      return missions.filter((m) => m.status === 'Not started');
    case 'completed':
      return missions.filter((m) => m.status === 'Completed');
    default:
      return missions;
  }
}

export const MissionCenter = ({ onXpAwarded }: MissionCenterProps) => {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [activeTab, setActiveTab] = useState('all');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Mission | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  const fetchMissions = async () => {
    setLoading(true);
    try {
      const data = await endpoints.missions.list();
      setMissions(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMissions();
  }, []);

  const tabFiltered = filterMissions(missions, activeTab);

  const filtered = tabFiltered.filter((m) => {
    if (searchQuery && !m.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (priorityFilter && m.priority !== priorityFilter) return false;
    return true;
  });

  const tabsWithCounts = TABS.map((t) => ({
    ...t,
    count: filterMissions(missions, t.id).length,
  }));

  const handleComplete = (mission: Mission) => {
    setMissions((prev) => prev.map((m) => (m.id === mission.id ? mission : m)));
    onXpAwarded?.();
  };

  const handleDelete = (mission: Mission) => {
    setMissions((prev) => prev.filter((m) => m.id !== mission.id));
  };

  const handleUpdated = (mission: Mission) => {
    setMissions((prev) => prev.map((m) => (m.id === mission.id ? mission : m)));
    setEditing(null);
  };

  const handleCreated = (newMission: Mission) => {
    setMissions((prev) => [...prev, newMission]);
    setShowForm(false);
  };

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h2 style={{ fontFamily: 'monospace', color: '#fff', margin: 0 }}>
          🎯 Mission Center
        </h2>
        {!showForm && !editing && (
          <RpgButton variant="orange" onClick={() => setShowForm(true)}>
            + New Mission
          </RpgButton>
        )}
      </div>

      {(showForm || editing) && (
        <div style={{ marginBottom: '16px' }}>
          <MissionCreateForm
            editing={editing ?? undefined}
            onCreated={editing ? handleUpdated : handleCreated}
            onCancel={() => { setShowForm(false); setEditing(null); }}
          />
        </div>
      )}

      <RpgTabs tabs={tabsWithCounts} activeTab={activeTab} onChange={setActiveTab} />

      <div
        style={{
          display: 'flex',
          gap: '8px',
          marginBottom: '12px',
          marginTop: '12px',
          alignItems: 'center',
        }}
      >
        <input
          type="text"
          placeholder="Search missions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ ...INPUT_STYLE, maxWidth: 240 }}
        />
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          style={{ ...INPUT_STYLE, width: 140 }}
        >
          <option value="">All Priorities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        {(searchQuery || priorityFilter) && (
          <button
            onClick={() => { setSearchQuery(''); setPriorityFilter(''); }}
            style={{
              background: 'transparent',
              border: '1px solid #3a3a3a',
              color: '#b0b0b0',
              padding: '6px 10px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
              fontFamily: 'monospace',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {loading ? (
        <div className="rpg-empty">
          <p className="rpg-empty-text">Loading missions...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rpg-empty" style={{ marginTop: '16px' }}>
          <div className="rpg-empty-icon">🎯</div>
          <p className="rpg-empty-text">
            {activeTab === 'all' && 'No missions yet. Create your first mission!'}
            {activeTab === 'in_progress' && 'No missions in progress. Start one!'}
            {activeTab === 'not_started' && 'No pending missions. All caught up!'}
            {activeTab === 'completed' && 'No completed missions yet. Complete one to see it here!'}
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            marginTop: '12px',
          }}
        >
          {filtered.map((mission) => (
            <MissionCard
              key={mission.id}
              mission={mission}
              onComplete={handleComplete}
              onDelete={handleDelete}
              onEdit={(m) => { setEditing(m); setShowForm(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
