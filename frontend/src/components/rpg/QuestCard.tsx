import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgBadge } from './RpgBadge';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { Quest } from '../../services/api';

interface QuestCardProps {
  quest: Quest;
  onComplete?: (quest: Quest) => void;
  onDelete?: (quest: Quest) => void;
  onEdit?: (quest: Quest) => void;
}

export const QuestCard = ({ quest, onComplete, onDelete, onEdit }: QuestCardProps) => {
  const [completing, setCompleting] = useState(false);
  const [flash, setFlash] = useState(false);
  const { toast } = useToast();

  const statusVariant =
    quest.status === 'Completed' ? 'green' : quest.status === 'In progress' ? 'orange' : 'red';

  const priorityVariant =
    quest.priority === 'High' ? 'red' : quest.priority === 'Medium' ? 'orange' : 'green';

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const completedQuest = await endpoints.quests.complete(quest.id);
      setFlash(true);
      toast(`Quest Complete! +${completedQuest.xp_reward} XP`, 'success');
      setTimeout(() => setFlash(false), 500);
      onComplete?.(completedQuest);
    } finally {
      setCompleting(false);
    }
  };

  const handleDelete = () => {
    if (!window.confirm('Delete this quest?')) return;
    endpoints.quests.delete(quest.id).then(() => onDelete?.(quest));
  };

  return (
    <RpgCard className={flash ? 'qc-done-flash' : ''}>
      <h3 style={{ color: '#fff', margin: '0 0 4px 0' }}>{quest.title}</h3>

      {quest.description && (
        <p style={{ color: '#b0b0b0', fontSize: '0.85rem', margin: '0 0 8px 0' }}>
          {quest.description}
        </p>
      )}

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
        <RpgBadge variant={statusVariant}>{quest.status}</RpgBadge>
        <RpgBadge variant={priorityVariant}>{quest.priority}</RpgBadge>
        {quest.category && <RpgBadge variant="orange">{quest.category}</RpgBadge>}
        <RpgBadge variant="gold">+{quest.xp_reward} XP</RpgBadge>
      </div>

      <div style={{ fontSize: '0.75rem', color: '#707070', marginBottom: '8px' }}>
        {quest.due_date && <span style={{ marginRight: '12px' }}>Due: {quest.due_date}</span>}
        {quest.time_estimate && <span>{quest.time_estimate} min</span>}
      </div>

      <div
        style={{
          display: 'flex',
          gap: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #2a2a2a',
        }}
      >
        {quest.status !== 'Completed' && (
          <RpgButton variant="green" size="sm" disabled={completing} onClick={handleComplete}>
            {completing ? 'Completing...' : 'Complete'}
          </RpgButton>
        )}
        {onEdit && (
          <RpgButton variant="ghost" size="sm" onClick={() => onEdit(quest)} aria-label={`Edit quest: ${quest.title}`}>
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
