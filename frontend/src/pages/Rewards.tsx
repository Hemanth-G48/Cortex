import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { RpgLayout } from '../components/rpg/RpgLayout';
import { RpgCard } from '../components/rpg/RpgCard';
import { RpgBadge } from '../components/rpg/RpgBadge';
import { RpgButton } from '../components/rpg/RpgButton';
import { RpgTabs } from '../components/rpg/RpgTabs';
import { endpoints } from '../services/api';
import type { Reward } from '../services/api';

const sidebar = (
  <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
    <Link to="/character" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>👤</span> Profile
    </Link>
    <Link to="/quests" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>⚔️</span> Quests
    </Link>
    <Link to="/missions" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>🎯</span> Missions
    </Link>
    <Link to="/rewards" className="sidebar-link active" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>🎁</span> Rewards
    </Link>
    <Link to="/rpg-dashboard" className="sidebar-link" style={{ textDecoration: 'none', color: 'inherit' }}>
      <span>📊</span> Dashboard
    </Link>
  </nav>
);

type TabId = 'available' | 'claimed';

export const Rewards = () => {
  const [allRewards, setAllRewards] = useState<Reward[]>([]);
  const [claimed, setClaimed] = useState<Reward[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>('available');
  const [claimingId, setClaimingId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    endpoints.rewards.list(true).then(setAllRewards).catch(() => {});
    endpoints.rewards.claimed().then(setClaimed).catch(() => {});
  }, []);

  const handleClaim = async (rewardId: number) => {
    setClaimingId(rewardId);
    setMessage(null);
    try {
      await endpoints.rewards.claim(rewardId, 1);
      setMessage(`Reward claimed!`);
      endpoints.rewards.list(true).then(setAllRewards).catch(() => {});
      endpoints.rewards.claimed().then(setClaimed).catch(() => {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to claim reward';
      setMessage(msg);
    } finally {
      setClaimingId(null);
    }
  };

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: 'available', label: 'Available', count: allRewards.length },
    { id: 'claimed', label: 'Claimed', count: claimed.length },
  ];

  const currentRewards = activeTab === 'available' ? allRewards : claimed;

  return (
    <RpgLayout sidebar={sidebar}>
      <div style={{ maxWidth: '700px', margin: '0 auto' }}>
        <h2 className="pixel-text" style={{ color: '#ff9800', fontSize: '1rem', marginBottom: '16px' }}>
          🎁 Rewards Vault
        </h2>

        {message && (
          <div
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              background: message.startsWith('Claimed') ? 'var(--rpg-success-muted)' : 'var(--rpg-danger-muted)',
              color: message.startsWith('Claimed') ? 'var(--rpg-success)' : 'var(--rpg-danger)',
              fontSize: '0.8rem',
              marginBottom: '12px',
            }}
          >
            {message}
          </div>
        )}

        <RpgTabs tabs={tabs} activeTab={activeTab} onChange={(id) => setActiveTab(id as TabId)} />

        {currentRewards.length === 0 ? (
          <div className="rpg-empty">
            <div className="rpg-empty-icon">🎁</div>
            <div className="rpg-empty-text">
              {activeTab === 'available' ? 'No rewards available right now.' : 'No claimed rewards yet.'}
            </div>
          </div>
        ) : (
          <div className="card-grid">
            {currentRewards.map((r) => (
              <RpgCard key={r.id} style={{ borderLeft: `3px solid ${r.is_available ? '#ff9800' : '#4caf50'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <h3 style={{ margin: 0, fontSize: '0.95rem' }}>{r.title}</h3>
                  <RpgBadge variant="gold">+{r.xp_cost} XP</RpgBadge>
                </div>
                {r.description && (
                  <p style={{ fontSize: '0.78rem', color: 'var(--rpg-text-secondary)', marginBottom: '8px' }}>
                    {r.description}
                  </p>
                )}
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {r.category && <RpgBadge variant="orange">{r.category}</RpgBadge>}
                  {!r.is_available && <RpgBadge variant="green">Claimed</RpgBadge>}
                  {r.is_available && (
                    <RpgButton
                      variant="green"
                      size="sm"
                      onClick={() => handleClaim(r.id)}
                      disabled={claimingId === r.id}
                    >
                      {claimingId === r.id ? '...' : 'Claim'}
                    </RpgButton>
                  )}
                </div>
              </RpgCard>
            ))}
          </div>
        )}
      </div>
    </RpgLayout>
  );
};
