import { useState, useEffect } from 'react';
import { RpgTabs } from './RpgTabs';
import { QuestCard } from './QuestCard';
import { QuestCreateForm } from './QuestCreateForm';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Quest } from '../../services/api';

interface QuestCenterProps {
  onXpAwarded?: () => void;
}

const TABS = [
  { id: 'inbox', label: 'Inbox' },
  { id: 'today', label: 'Today' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'overdue', label: 'Overdue' },
];

function getToday(): string {
  return new Date().toISOString().split('T')[0];
}

function filterQuests(quests: Quest[], tab: string): Quest[] {
  const today = getToday();
  switch (tab) {
    case 'inbox':
      return quests.filter(
        (q) => q.status === 'Not started' && (!q.due_date || q.due_date > today)
      );
    case 'today':
      return quests.filter((q) => q.due_date === today && q.status !== 'Completed');
    case 'in_progress':
      return quests.filter((q) => q.status === 'In progress');
    case 'overdue':
      return quests.filter(
        (q) => q.status !== 'Completed' && q.due_date != null && q.due_date < today
      );
    default:
      return quests;
  }
}

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

export const QuestCenter = ({ onXpAwarded }: QuestCenterProps) => {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [activeTab, setActiveTab] = useState('inbox');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Quest | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');

  const fetchQuests = async () => {
    setLoading(true);
    try {
      const data = await endpoints.quests.list();
      setQuests(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuests();
  }, []);

  const tabFiltered = filterQuests(quests, activeTab);

  const filtered = tabFiltered.filter((q) => {
    if (searchQuery && !q.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (categoryFilter && q.category !== categoryFilter) return false;
    if (priorityFilter && q.priority !== priorityFilter) return false;
    return true;
  });

  const tabsWithCounts = TABS.map((t) => ({
    ...t,
    count: filterQuests(quests, t.id).length,
  }));

  const handleComplete = (quest: Quest) => {
    setQuests((prev) => prev.map((q) => (q.id === quest.id ? quest : q)));
    onXpAwarded?.();
  };

  const handleDelete = (quest: Quest) => {
    setQuests((prev) => prev.filter((q) => q.id !== quest.id));
  };

  const handleCreated = (newQuest: Quest) => {
    setQuests((prev) => [...prev, newQuest]);
    setShowForm(false);
  };

  const handleUpdated = (updated: Quest) => {
    setQuests((prev) => prev.map((q) => (q.id === updated.id ? updated : q)));
    setEditing(null);
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
        <h2 style={{ fontFamily: 'monospace', color: '#fff', margin: 0 }}>Quest Center</h2>
        {!showForm && !editing && (
          <RpgButton variant="orange" onClick={() => setShowForm(true)}>
            + New Quest
          </RpgButton>
        )}
      </div>

      {(showForm || editing) && (
        <div style={{ marginBottom: '16px' }}>
          <QuestCreateForm
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
          placeholder="Search quests..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ ...INPUT_STYLE, maxWidth: 240 }}
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          style={{ ...INPUT_STYLE, width: 140 }}
        >
          <option value="">All Categories</option>
          <option value="Work">Work</option>
          <option value="Fitness">Fitness</option>
          <option value="Personal">Personal</option>
          <option value="Learning">Learning</option>
          <option value="Social">Social</option>
          <option value="Health">Health</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          style={{ ...INPUT_STYLE, width: 130 }}
        >
          <option value="">All Priorities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        {(searchQuery || categoryFilter || priorityFilter) && (
          <button
            onClick={() => { setSearchQuery(''); setCategoryFilter(''); setPriorityFilter(''); }}
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
          <p className="rpg-empty-text">Loading quests...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rpg-empty">
          <div className="rpg-empty-icon">📭</div>
          <p className="rpg-empty-text">
            {activeTab === 'inbox' && 'No quests in your inbox. Add a new quest!'}
            {activeTab === 'today' && 'No quests due today. Enjoy your free day!'}
            {activeTab === 'in_progress' && 'No quests in progress. Start one!'}
            {activeTab === 'overdue' && 'Nothing overdue. Great work!'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
          {filtered.map((quest) => (
            <QuestCard
              key={quest.id}
              quest={quest}
              onComplete={handleComplete}
              onDelete={handleDelete}
              onEdit={(q) => { setEditing(q); setShowForm(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
