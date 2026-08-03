import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { Quest } from '../../services/api';

interface QuestCreateFormProps {
  onCreated: (quest: Quest) => void;
  onCancel?: () => void;
  /** When set, the form is pre-filled and submits an update instead of a create. */
  editing?: Quest;
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

export const QuestCreateForm = ({ onCreated, onCancel, editing }: QuestCreateFormProps) => {
  const [title, setTitle] = useState(editing?.title ?? '');
  const [description, setDescription] = useState(editing?.description ?? '');
  const [category, setCategory] = useState(editing?.category ?? '');
  const [priority, setPriority] = useState(editing?.priority ?? 'Medium');
  const [timeEstimate, setTimeEstimate] = useState(editing?.time_estimate ?? 30);
  const [dueDate, setDueDate] = useState(editing?.due_date ?? '');
  const [xpReward, setXpReward] = useState(editing?.xp_reward ?? 50);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      alert('Title is required');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        title,
        description,
        category: category || null,
        priority,
        time_estimate: timeEstimate,
        due_date: dueDate || null,
        xp_reward: xpReward,
        status: editing?.status ?? 'Not started',
      };
      const savedQuest = editing
        ? await endpoints.quests.update(editing.id, payload)
        : await endpoints.quests.create(payload);
      onCreated(savedQuest);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create quest';
      alert(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <RpgCard>
      <h2 style={{ fontFamily: 'monospace', color: '#fff', marginBottom: 20 }}>{editing ? 'Edit Quest' : 'New Quest'}</h2>
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
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={inputStyle}
            >
              <option value="">--</option>
              <option value="Work">Work</option>
              <option value="Fitness">Fitness</option>
              <option value="Personal">Personal</option>
              <option value="Learning">Learning</option>
              <option value="Social">Social</option>
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

        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Time Estimate</label>
            <input
              type="number"
              value={timeEstimate}
              onChange={(e) => setTimeEstimate(Number(e.target.value))}
              min={5}
              max={480}
              style={inputStyle}
            />
            <span style={{ color: '#b0b0b0', fontSize: 12, fontFamily: 'monospace' }}>min</span>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>XP Reward</label>
            <input
              type="number"
              value={xpReward}
              onChange={(e) => setXpReward(Number(e.target.value))}
              min={0}
              max={9999}
              style={inputStyle}
            />
          </div>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Due Date</label>
          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div
          style={{
            display: 'flex',
            gap: 8,
            justifyContent: 'flex-end',
            borderTop: '1px solid #3a3a3a',
            paddingTop: 12,
            marginTop: 8,
          }}
        >
          <RpgButton type="button" onClick={onCancel} variant="ghost">
            Cancel
          </RpgButton>
          <RpgButton type="submit" disabled={submitting}>
            {submitting ? 'Saving...' : editing ? 'Update' : 'Create'}
          </RpgButton>
        </div>
      </form>
    </RpgCard>
  );
};
