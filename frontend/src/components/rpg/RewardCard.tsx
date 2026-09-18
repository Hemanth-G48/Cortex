import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgBadge } from './RpgBadge';
import { RpgButton } from './RpgButton';
import { useToast } from '../../hooks/useToast';
import { confirmDelete } from '../../utils/confirm';
import type { Reward } from '../../services/api';

interface RewardCardProps {
  reward: Reward;
  characterXp: number;
  onClaim?: (reward: Reward) => void;
  onDelete?: (reward: Reward) => void;
  onEdit?: (reward: Reward) => void;
}

export const RewardCard = ({ reward, characterXp, onClaim, onDelete, onEdit }: RewardCardProps) => {
  const [flash, setFlash] = useState(false);
  const { toast } = useToast();
  const isClaimed = !reward.is_available || !!reward.claimed_date;
  const isAffordable = characterXp >= reward.xp_cost;
  const unlocked = !isClaimed && isAffordable;

  const statusVariant = isClaimed ? 'green' : unlocked ? 'gold' : 'red';
  const statusLabel = isClaimed ? 'Claimed' : unlocked ? 'Available' : 'Not available';

  const handleClaim = () => {
    if (unlocked) {
      setFlash(true);
      toast(`Reward unlocked! Claimed ${reward.title}`, 'success');
      setTimeout(() => setFlash(false), 500);
    }
    onClaim?.(reward);
  };

  const handleDelete = () => {
    if (!confirmDelete('this reward')) return;
    onDelete?.(reward);
  };

  return (
    <RpgCard className={`${flash ? 'qc-done-flash' : ''} ${unlocked ? 'qc-reward-unlocked' : ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h3 style={{ color: '#fff', margin: 0 }}>{reward.title}</h3>
        <RpgBadge variant="gold">{reward.xp_cost} XP</RpgBadge>
      </div>

      {reward.description && (
        <p style={{ color: '#b0b0b0', fontSize: '0.85rem', margin: '4px 0 8px 0' }}>
          {reward.description}
        </p>
      )}

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
        {reward.category && <RpgBadge variant="orange">{reward.category}</RpgBadge>}
        <RpgBadge variant={statusVariant}>{statusLabel}</RpgBadge>
      </div>
      {!unlocked && !isClaimed && (
        <div style={{ fontSize: '0.72rem', color: '#ef4444', fontWeight: 700, marginBottom: '8px' }}>
          Not available — need {reward.xp_cost} XP (have {characterXp})
        </div>
      )}

      {reward.claimed_date && (
        <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '8px' }}>
          Claimed: {reward.claimed_date}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          gap: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #2a2a2a',
        }}
      >
        {!isClaimed && (
          <RpgButton variant="green" size="sm" disabled={!isAffordable} onClick={handleClaim}>
            Claim
          </RpgButton>
        )}
        {onEdit && (
          <RpgButton variant="ghost" size="sm" onClick={() => onEdit(reward)} aria-label={`Edit reward: ${reward.title}`}>
            ✎ Edit
          </RpgButton>
        )}
        <RpgButton variant="ghost" size="sm" onClick={handleDelete}>
          Delete
        </RpgButton>
      </div>
    </RpgCard>
  );
};