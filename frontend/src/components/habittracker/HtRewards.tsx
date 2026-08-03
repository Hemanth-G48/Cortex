import { useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { Reward } from '../../services/api';

interface Props {
  rewards: Reward[];
  totalXp: number;
  onClaimed?: () => void;
}

/**
 * Compact sidebar rewards list (Phase 58-59): thumbnail, "XP Needed: X" and a
 * "Claim Reward" button that pulses gold when affordable.
 */
export const HtRewards = ({ rewards, totalXp, onClaimed }: Props) => {
  const { toast } = useToast();
  const [claiming, setClaiming] = useState<number | null>(null);

  const claim = async (reward: Reward) => {
    if (claiming === reward.id) return;
    setClaiming(reward.id);
    try {
      await endpoints.rewards.claim(reward.id, 1);
      toast(`Reward claimed! 🎉 ${reward.title}`, 'success');
      onClaimed?.();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not claim reward', 'error');
    } finally {
      setClaiming(null);
    }
  };

  return (
    <div className="ht-card">
      <div className="ht-card-title">Rewards</div>
      {rewards.length === 0 ? (
        <div className="ht-cal-empty">No rewards available — earn XP to unlock.</div>
      ) : (
        <div className="ht-rewards-list">
          {rewards.map((r) => {
            const affordable = totalXp >= r.xp_cost;
            return (
              <div key={r.id} className={`ht-reward-item${affordable ? ' affordable' : ''}`}>
                <div className="ht-reward-thumb" aria-hidden="true">
                  {r.image_url ? <img src={r.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }} /> : '🎁'}
                </div>
                <div className="ht-reward-body">
                  <div className="ht-reward-name">{r.title}</div>
                  <div className="ht-reward-cost">XP Needed: {r.xp_cost}</div>
                </div>
                <button
                  type="button"
                  className={`ht-claim-btn${affordable ? ' affordable' : ''}`}
                  disabled={!affordable || claiming === r.id}
                  onClick={() => void claim(r)}
                  aria-label={`Claim ${r.title} for ${r.xp_cost} XP`}
                >
                  {claiming === r.id ? '…' : 'Claim Reward'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
