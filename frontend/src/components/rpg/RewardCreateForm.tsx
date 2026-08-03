import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Reward } from '../../services/api';

interface RewardCreateFormProps {
  onCreated: (reward: Reward) => void;
  onCancel?: () => void;
  /** When set, the form is pre-filled and submits an update instead of a create. */
  editing?: Reward;
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  backgroundColor: '#2a2a2a',
  border: '1px solid #3a3a3a',
  padding: '8px',
  borderRadius: 6,
  color: '#fff',
  fontSize: 14,
  boxSizing: 'border-box',
  outline: 'none',
};
const labelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: 4,
  color: '#b0b0b0',
  fontSize: 13,
  fontFamily: 'monospace',
};
const fieldStyle: React.CSSProperties = { marginBottom: 12 };

export function RewardCreateForm({ onCreated, onCancel, editing }: RewardCreateFormProps) {
  const [title, setTitle] = useState(editing?.title ?? '');
  const [description, setDescription] = useState(editing?.description ?? '');
  const [category, setCategory] = useState(editing?.category ?? '');
  const [xpCost, setXpCost] = useState(editing?.xp_cost ?? 100);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { alert('Title is required'); return; }
    setSubmitting(true);
    try {
      const payload = {
        title,
        description: description || null,
        category: category || undefined,
        xp_cost: xpCost,
        is_available: editing?.is_available ?? true,
      };
      const created = editing
        ? await endpoints.rewards.update(editing.id, payload)
        : await endpoints.rewards.create(payload);
      onCreated(created);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create reward');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RpgCard>
      <h2 style={{ fontFamily: 'monospace', color: '#fff', marginBottom: 20 }}>{editing ? 'Edit Reward' : 'New Reward'}</h2>
      <form onSubmit={handleSubmit}>
        <div style={fieldStyle}>
          <label style={labelStyle}>Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            style={inputStyle}
          />
        </div>
        <div style={fieldStyle}>
          <label style={labelStyle}>Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            style={inputStyle}
          />
        </div>
        <div style={{ display: 'flex', gap: 12, ...fieldStyle }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={inputStyle}
            >
              <option value="">--</option>
              <option value="Entertainment">Entertainment</option>
              <option value="Food">Food</option>
              <option value="Break">Break</option>
              <option value="Shopping">Shopping</option>
              <option value="Self Care">Self Care</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>XP Cost</label>
            <input
              type="number"
              min={10}
              max={9999}
              step={10}
              value={xpCost}
              onChange={(e) => setXpCost(Number(e.target.value))}
              style={inputStyle}
            />
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 12, borderTop: '1px solid #3a3a3a', marginTop: 12 }}>
          <RpgButton variant="ghost" onClick={onCancel} type="button">Cancel</RpgButton>
          <RpgButton variant="orange" type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : editing ? 'Update' : 'Create'}
          </RpgButton>
        </div>
      </form>
    </RpgCard>
  );
}
