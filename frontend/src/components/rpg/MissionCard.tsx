import { useState, useEffect } from 'react';
import { RpgCard } from './RpgCard';
import { RpgBadge } from './RpgBadge';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import { confirmDelete } from '../../utils/confirm';
import type { Mission, MissionTask, MissionVaultTaskSuggestion } from '../../services/api';

interface MissionCardProps {
  mission: Mission;
  onComplete?: (mission: Mission) => void;
  onDelete?: (mission: Mission) => void;
  onEdit?: (mission: Mission) => void;
}

export const MissionCard = ({ mission, onComplete, onDelete, onEdit }: MissionCardProps) => {
  const [tasks, setTasks] = useState<MissionTask[]>([]);
  // Defect #80: vault-mined subtask suggestions for this mission.
  const [vaultTasks, setVaultTasks] = useState<MissionVaultTaskSuggestion[]>([]);
  const [completing, setCompleting] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [flash, setFlash] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    endpoints.missions.listTasks(mission.id).then(setTasks);
    // Defect #80 fix: mine the vault for checklist items that belong to this mission.
    endpoints.missions
      .vaultTasks(mission.id)
      .then((r) => setVaultTasks(r.suggestions))
      .catch(() => setVaultTasks([]));
  }, [mission.id]);

  const statusVariant =
    mission.status === 'Completed' ? 'green' : mission.status === 'In progress' ? 'orange' : 'red';

  const priorityVariant =
    mission.priority === 'High' ? 'red' : mission.priority === 'Medium' ? 'orange' : 'green';

  const completedCount = tasks.filter((t) => t.completed).length;
  const totalCount = tasks.length;

  const handleComplete = async () => {
    setCompleting(true);
    try {
      const completed = await endpoints.missions.complete(mission.id);
      setFlash(true);
      toast(`Mission Complete! +${completed.xp_reward} XP`, 'success');
      setTimeout(() => setFlash(false), 500);
      onComplete?.(completed);
    } finally {
      setCompleting(false);
    }
  };

  const handleDelete = () => {
    if (!confirmDelete('this mission')) return;
    endpoints.missions.delete(mission.id).then(() => onDelete?.(mission));
  };

  const handleAddTask = async () => {
    if (!newTaskTitle.trim()) return;
    await endpoints.missions.createTask(mission.id, {
      title: newTaskTitle.trim(),
      sort_order: tasks.length,
    });
    setNewTaskTitle('');
    const updated = await endpoints.missions.listTasks(mission.id);
    setTasks(updated);
  };

  const handleToggleTask = async (taskId: number, completed: boolean) => {
    await endpoints.missions.updateTask(taskId, { completed });
    const updated = await endpoints.missions.listTasks(mission.id);
    setTasks(updated);
  };

  const handleDeleteTask = async (taskId: number) => {
    if (!confirmDelete('this subtask')) return;
    await endpoints.missions.deleteTask(taskId);
    const updated = await endpoints.missions.listTasks(mission.id);
    setTasks(updated);
  };

  // Defect #80: accept a vault suggestion → create a real MissionTask.
  const handleAddVaultTask = async (title: string) => {
    await endpoints.missions.createTask(mission.id, {
      title,
      sort_order: tasks.length,
    });
    const updated = await endpoints.missions.listTasks(mission.id);
    setTasks(updated);
    setVaultTasks((prev) => prev.filter((s) => s.title !== title));
  };

  const taskRowStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
    fontSize: '0.8rem',
  };

  return (
    <RpgCard className={flash ? 'qc-done-flash' : ''}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ color: '#fff', margin: 0 }}>{mission.title}</h3>
        <RpgBadge variant="gold">+{mission.xp_reward} XP</RpgBadge>
      </div>

      {mission.description && (
        <p style={{ color: '#b0b0b0', fontSize: '0.85rem', margin: '4px 0 8px 0' }}>
          {mission.description}
        </p>
      )}

      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
        <RpgBadge variant={statusVariant}>{mission.status}</RpgBadge>
        <RpgBadge variant={priorityVariant}>{mission.priority}</RpgBadge>
        {mission.mission_type && <RpgBadge variant="orange">{mission.mission_type}</RpgBadge>}
        {mission.linked_quests && <RpgBadge variant="gold">🔗 linked</RpgBadge>}
      </div>

      <div style={{ fontSize: '0.75rem', color: '#707070', marginBottom: '8px' }}>
        {mission.due_date ? <span>Due: {mission.due_date}</span> : <span>No deadline</span>}
      </div>

      {totalCount > 0 && (
        <>
          <div className="rpg-progress-bar" style={{ marginBottom: '4px' }}>
            <div
              className="rpg-progress-fill-green"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
          <div style={{ fontSize: '0.7rem', color: '#707070', marginBottom: '8px' }}>
            {completedCount}/{totalCount} subtasks
          </div>
        </>
      )}

      {tasks.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          {tasks.map((t) => (
            <div key={t.id} style={taskRowStyle}>
              <input
                type="checkbox"
                checked={t.completed}
                onChange={() => handleToggleTask(t.id, !t.completed)}
              />
              <span
                style={{
                  flex: 1,
                  textDecoration: t.completed ? 'line-through' : 'none',
                  color: t.completed ? '#606060' : '#ccc',
                }}
              >
                {t.title}
              </span>
              <button
                onClick={() => handleDeleteTask(t.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#888',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  padding: '0 4px',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#ff4444')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#888')}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {vaultTasks.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontSize: '0.7rem', color: '#808080', marginBottom: '4px' }}>
            📚 Suggested from your vault
          </div>
          {vaultTasks.map((s) => (
            <div key={`${s.document_id}-${s.title}`} style={taskRowStyle}>
              <button
                type="button"
                onClick={() => void handleAddVaultTask(s.title)}
                title={s.document_title ? `From: ${s.document_title}` : undefined}
                style={{
                  background: 'transparent',
                  border: '1px solid #333',
                  color: '#888',
                  cursor: 'pointer',
                  fontSize: '0.7rem',
                  borderRadius: '4px',
                  padding: '0 4px',
                }}
              >
                +
              </button>
              <span style={{ flex: 1, color: '#999' }}>{s.title}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
        <input
          type="text"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          placeholder="Add subtask..."
          onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
          style={{
            flex: 1,
            background: '#1a1a1a',
            border: '1px solid #333',
            color: '#ccc',
            padding: '4px 8px',
            fontSize: '0.8rem',
            borderRadius: '4px',
            outline: 'none',
          }}
        />
        <RpgButton variant="ghost" size="sm" onClick={handleAddTask}>
          Add
        </RpgButton>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #2a2a2a',
        }}
      >
        {mission.status !== 'Completed' && (
          <RpgButton variant="green" size="sm" disabled={completing} onClick={handleComplete}>
            {completing ? 'Completing...' : 'Complete'}
          </RpgButton>
        )}
        {onEdit && (
          <RpgButton variant="ghost" size="sm" onClick={() => onEdit(mission)} aria-label={`Edit mission: ${mission.title}`}>
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
