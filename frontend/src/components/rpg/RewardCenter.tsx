import { useState, useEffect, useCallback } from 'react';
import { RpgTabs } from './RpgTabs';
import { RewardCard } from './RewardCard';
import { RewardCreateForm } from './RewardCreateForm';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Reward, Character } from '../../services/api';

const TABS = [
  { id: 'available', label: 'Rewards' },
  { id: 'claimed', label: 'Claimed' },
];

const INPUT_STYLE: React.CSSProperties = {
  width: '100%', backgroundColor: '#2a2a2a', border: '1px solid #3a3a3a',
  padding: '8px 10px', borderRadius: 6, color: '#fff', fontSize: 13,
  boxSizing: 'border-box', outline: 'none',
};

export const RewardCenter = () => {
  const [allRewards, setAllRewards] = useState<Reward[]>([]);
  const [claimed, setClaimed] = useState<Reward[]>([]);
  const [character, setCharacter] = useState<Character | null>(null);
  const [activeTab, setActiveTab] = useState('available');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Reward | null>(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [confettiKey, setConfettiKey] = useState(0);
  const [sortBy, setSortBy] = useState<'cost-asc' | 'cost-desc' | ''>('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [rewards, claimedRewards, char] = await Promise.all([
        endpoints.rewards.list(true),
        endpoints.rewards.claimed(),
        endpoints.characters.get(1),
      ]);
      setAllRewards(rewards);
      setClaimed(claimedRewards);
      setCharacter(char);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleClaim = async (reward: Reward) => {
    try {
      await endpoints.rewards.claim(reward.id, 1);
      setShowConfetti(true);
      setConfettiKey((k) => k + 1);
      setTimeout(() => setShowConfetti(false), 1000);
      await fetchData();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to claim');
    }
  };

  const handleDelete = async (reward: Reward) => {
    if (!window.confirm('Delete this reward?')) return;
    await endpoints.rewards.delete(reward.id);
    await fetchData();
  };

  const handleCreated = (newReward: Reward) => {
    setAllRewards((prev) => [...prev, newReward]);
    setShowForm(false);
  };

  const handleUpdated = async () => {
    await fetchData();
    setEditing(null);
  };

  const characterXp = character?.xp ?? 0;

  let displayRewards = activeTab === 'available' ? allRewards : claimed;

  if (categoryFilter) {
    displayRewards = displayRewards.filter((r) => r.category === categoryFilter);
  }
  if (sortBy === 'cost-asc') {
    displayRewards = [...displayRewards].sort((a, b) => a.xp_cost - b.xp_cost);
  } else if (sortBy === 'cost-desc') {
    displayRewards = [...displayRewards].sort((a, b) => b.xp_cost - a.xp_cost);
  }

  const tabsWithCounts = TABS.map((t) => ({
    ...t,
    count: t.id === 'available' ? allRewards.length : claimed.length,
  }));

  return (
    <div style={{ position: 'relative' }}>
      {showConfetti && (
        <div className="rpg-confetti-container" key={confettiKey}>
          <div className="rpg-confetti-piece" />
          <div className="rpg-confetti-piece" />
          <div className="rpg-confetti-piece" />
          <div className="rpg-confetti-piece" />
          <div className="rpg-confetti-piece" />
          <div className="rpg-confetti-piece" />
        </div>
      )}

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px',
        }}
      >
        <h2 style={{ fontFamily: 'monospace', color: '#fff', margin: 0 }}>
          🎁 Rewards Vault
        </h2>
        {!showForm && !editing && (
          <RpgButton variant="orange" onClick={() => setShowForm(true)}>
            + New Reward
          </RpgButton>
        )}
      </div>

      {(showForm || editing) && (
        <div style={{ marginBottom: '16px' }}>
          <RewardCreateForm
            editing={editing ?? undefined}
            onCreated={editing ? handleUpdated : handleCreated}
            onCancel={() => { setShowForm(false); setEditing(null); }}
          />
        </div>
      )}

      <RpgTabs tabs={tabsWithCounts} activeTab={activeTab} onChange={setActiveTab} />

      <div
        style={{
          display: 'flex', gap: '8px', marginBottom: '12px',
          marginTop: '12px', alignItems: 'center',
        }}
      >
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          style={{ ...INPUT_STYLE, width: 160 }}
        >
          <option value="">Default Order</option>
          <option value="cost-asc">XP: Low to High</option>
          <option value="cost-desc">XP: High to Low</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          style={{ ...INPUT_STYLE, width: 140 }}
        >
          <option value="">All Categories</option>
          <option value="Entertainment">Entertainment</option>
          <option value="Food">Food</option>
          <option value="Break">Break</option>
          <option value="Shopping">Shopping</option>
          <option value="Self Care">Self Care</option>
          <option value="Other">Other</option>
        </select>
        {(sortBy || categoryFilter) && (
          <button
            onClick={() => { setSortBy(''); setCategoryFilter(''); }}
            style={{
              background: 'transparent', border: '1px solid #3a3a3a',
              color: '#b0b0b0', padding: '6px 10px', borderRadius: 6,
              cursor: 'pointer', fontSize: 12, fontFamily: 'monospace',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {loading ? (
        <div className="rpg-empty">
          <p className="rpg-empty-text">Loading rewards...</p>
        </div>
      ) : displayRewards.length === 0 ? (
        <div className="rpg-empty" style={{ marginTop: '16px' }}>
          <div className="rpg-empty-icon">🎁</div>
          <p className="rpg-empty-text">
            {activeTab === 'available'
              ? 'No rewards available. Create your first reward!'
              : 'No claimed rewards yet. Go earn some XP!'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
          {displayRewards.map((reward) => (
            <RewardCard
              key={reward.id}
              reward={reward}
              characterXp={characterXp}
              onClaim={handleClaim}
              onDelete={handleDelete}
              onEdit={(r) => { setEditing(r); setShowForm(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
};
