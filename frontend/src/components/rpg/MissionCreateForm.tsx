import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Mission } from '../../services/api';

interface MissionCreateFormProps {
  onCreated: (mission: Mission) => void;
  onCancel?: () => void;
  /** When set, the form is pre-filled and submits an update instead of a create. */
  editing?: Mission;
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

export function MissionCreateForm({ onCreated, onCancel, editing }: MissionCreateFormProps) {
  const [title, setTitle] = useState(editing?.title ?? '');
  const [description, setDescription] = useState(editing?.description ?? '');
  const [missionType, setMissionType] = useState(editing?.mission_type ?? '');
  const [priority, setPriority] = useState(editing?.priority ?? 'Medium');
  const [dueDate, setDueDate] = useState(editing?.due_date ?? '');
  const [xpReward, setXpReward] = useState(editing?.xp_reward ?? 100);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) { alert('Title is required'); return; }
    setSubmitting(true);
    try {
      const payload = {
        title, description: description || null,
        mission_type: missionType || null, priority,
        due_date: dueDate || null, xp_reward: xpReward,
        status: editing?.status ?? 'Not started',
      };
      const created = editing
        ? await endpoints.missions.update(editing.id, payload)
        : await endpoints.missions.create(payload);
      onCreated(created);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create mission');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RpgCard>
      <h2 style={{ fontFamily: 'monospace', color: '#fff', marginBottom: 20 }}>{editing ? 'Edit Mission' : 'New Mission'}</h2>
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
            <label style={labelStyle}>Mission Type</label>
            <select
              value={missionType}
              onChange={(e) => setMissionType(e.target.value)}
              style={inputStyle}
            >
              <option value="">--</option>
              <option value="Side Project">Side Project</option>
              <option value="Work Project">Work Project</option>
              <option value="Personal">Personal</option>
              <option value="Learning">Learning</option>
              <option value="Health">Health</option>
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              style={inputStyle}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, ...fieldStyle }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>XP Reward</label>
            <input
              type="number"
              min={0}
              max={9999}
              value={xpReward}
              onChange={(e) => setXpReward(Number(e.target.value))}
              style={inputStyle}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Due Date</label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 12, borderTop: '1px solid #3a3a3a' }}>
          <RpgButton variant="ghost" onClick={onCancel} type="button">Cancel</RpgButton>
          <RpgButton variant="orange" type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : editing ? 'Update' : 'Create'}
          </RpgButton>
        </div>
      </form>
    </RpgCard>
  );
}
