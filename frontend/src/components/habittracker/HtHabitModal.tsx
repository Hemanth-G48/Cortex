import { useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';

interface Props {
  kind: 'good' | 'bad';
  onClose: () => void;
  onCreated: () => void;
}

/** Good/Bad habit create modal (Phase 63): posts with habit_type + XP values. */
export const HtHabitModal = ({ kind, onClose, onCreated }: Props) => {
  const { toast } = useToast();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [xp, setXp] = useState(kind === 'good' ? 30 : 20);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      await endpoints.habits.create({
        name: name.trim(),
        description: description.trim() || null,
        habit_type: kind,
        xp_reward: kind === 'good' ? xp : 30,
        xp_penalty: kind === 'bad' ? xp : 20,
        frequency: 'daily',
        target_count: 1,
        user_id: 1,
      });
      toast(`New ${kind} habit created! ${kind === 'good' ? '🌱' : '⚠️'}`, 'success');
      onCreated();
      onClose();
    } catch {
      toast('Could not create habit', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal ht-pixel-corner" role="dialog" aria-modal="true" aria-label={`New ${kind} habit`} onClick={(e) => e.stopPropagation()}>
        {/* Phase 68: pixel-art placeholder above the form. */}
        <div className="ht-empty-icon" style={{ width: 48, height: 48, fontSize: '1.5rem', margin: '0 auto 0.75rem' }} aria-hidden="true">
          {kind === 'good' ? '🌱' : '🌑'}
        </div>
        <div className="modal-title">{kind === 'good' ? 'New Good Habit' : 'New Bad Habit'}</div>

        <label style={{ display: 'block', marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={kind === 'good' ? 'e.g. Deep Work' : 'e.g. Smoking'}
            style={{ width: '100%' }}
            autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') void submit(); if (e.key === 'Escape') onClose(); }}
          />
        </label>

        <label style={{ display: 'block', marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Description</span>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional"
            style={{ width: '100%' }}
          />
        </label>

        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {kind === 'good' ? 'XP reward' : 'XP penalty'}
          </span>
          <input
            type="number"
            min={0}
            value={xp}
            onChange={(e) => setXp(Math.max(0, Number(e.target.value)))}
            style={{ width: '80px' }}
          />
        </label>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button
            type="button"
            className="btn btn-primary"
            style={kind === 'bad' ? { background: 'var(--ht-bad)', borderColor: 'var(--ht-bad)' } : undefined}
            onClick={() => void submit()}
            disabled={!name.trim() || saving}
          >
            {saving ? 'Saving…' : `Create ${kind === 'good' ? 'Good' : 'Bad'} Habit`}
          </button>
        </div>
      </div>
    </div>
  );
};
