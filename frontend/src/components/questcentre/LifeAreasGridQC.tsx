import { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { endpoints } from '../../services/api';
import type { QuestCentreLifeArea } from '../../services/api';

interface Props {
  areas: QuestCentreLifeArea[];
  onChanged?: () => void;
}

const AREA_ICONS: Record<string, string> = {
  Work: '💼',
  Fitness: '🏋️',
  'Self Development': '📚',
  Health: '💚',
};

const editInputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: '#2a2a2a', border: '1px solid #3a3a3a', color: '#fff',
  padding: '6px 8px', borderRadius: 6, fontSize: 13, marginBottom: 8, outline: 'none',
};
const inputLabelStyle: React.CSSProperties = {
  display: 'block', marginBottom: 4, color: '#b0b0b0', fontSize: 12, fontFamily: 'monospace',
};

/**
 * Row-1 life-area grid (spec): 4 cards with a pixel-art backdrop, title,
 * "Complete in X days" subtitle, status badge and a mark-complete action.
 */
export const LifeAreasGridQC = ({ areas, onChanged }: Props) => {
  const { toast } = useToast();
  const [completing, setCompleting] = useState<number | null>(null);
  const [editing, setEditing] = useState<QuestCentreLifeArea | null>(null);
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [targetDays, setTargetDays] = useState('');
  const [saving, setSaving] = useState(false);

  const complete = async (id: number) => {
    if (completing === id) return;
    setCompleting(id);
    try {
      await endpoints.lifeAreas.complete(id);
      toast('Life area completed! 🎉', 'success');
      onChanged?.();
    } catch {
      toast('Could not complete life area', 'error');
    } finally {
      setCompleting(null);
    }
  };

  const startEdit = (area: QuestCentreLifeArea) => {
    setEditing(area);
    setName(area.name);
    setGoal(area.goal ?? '');
    setTargetDays(area.target_days != null ? String(area.target_days) : '');
  };

  const saveEdit = async () => {
    if (!editing || !name.trim()) return;
    setSaving(true);
    try {
      await endpoints.lifeAreas.update(editing.id, {
        name: name.trim(),
        goal: goal.trim() || null,
        target_days: targetDays ? Number(targetDays) : null,
      });
      toast('Life area updated', 'success');
      setEditing(null);
      onChanged?.();
    } catch {
      toast('Could not update life area', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (areas.length === 0) {
    return (
      <div className="qc-card">
        <div className="qc-card-title">Life Areas</div>
        <div className="qc-empty-pixel">
          <span className="qc-empty-icon">➕</span>
          <span>No life areas yet</span>
        </div>
      </div>
    );
  }

  return (
    <div className="qc-card">
      <div className="qc-card-title">Life Areas</div>
      {editing && (
        <div
          style={{
            marginBottom: '1rem', padding: '0.75rem',
            background: '#1e1e1e', border: '1px solid #282a2d', borderRadius: 8,
          }}
        >
          <div className="qc-card-title" style={{ fontSize: '0.8rem' }}>Edit Life Area</div>
          <label style={inputLabelStyle}>Name</label>
          <input style={editInputStyle} value={name} onChange={(e) => setName(e.target.value)} />
          <label style={inputLabelStyle}>Goal</label>
          <input style={editInputStyle} value={goal} onChange={(e) => setGoal(e.target.value)} />
          <label style={inputLabelStyle}>Target days</label>
          <input
            style={editInputStyle}
            type="number"
            min={1}
            value={targetDays}
            onChange={(e) => setTargetDays(e.target.value)}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: '0.75rem' }}>
            <button type="button" className="qc-btn qc-btn-gold" onClick={() => void saveEdit()} disabled={saving}>
              {saving ? 'Saving...' : 'Update'}
            </button>
            <button type="button" className="qc-btn" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="qc-life-grid">
        {areas.map((area) => {
          const done = area.status === 'Completed';
          const inProgress = area.status === 'In progress';
          const sub =
            done ? 'Completed'
            : area.complete_in_days != null ? `Complete in ${area.complete_in_days} day${area.complete_in_days === 1 ? '' : 's'}`
            : area.target_days != null ? `${area.target_days} day goal`
            : area.goal ?? null;

          return (
            <div key={area.id} className="qc-life-card">
              <div className="qc-life-backdrop" aria-hidden="true" />
              <div className="qc-life-content">
                <span className="qc-life-icon" aria-hidden="true">{AREA_ICONS[area.name] ?? '🎯'}</span>
                <span className="qc-life-name">{area.name}</span>
                {sub && <span className="qc-life-sub">{sub}</span>}
                <span className={`qc-status-badge ${done ? 'completed' : inProgress ? 'in-progress' : ''}`}>
                  {area.status}
                </span>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
                  <button
                    type="button"
                    className={`qc-life-complete-btn${done ? ' completed' : ''}`}
                    onClick={() => void complete(area.id)}
                    disabled={done}
                  >
                    {done ? '✓ Completed' : 'Complete'}
                  </button>
                  <button
                    type="button"
                    onClick={() => startEdit(area)}
                    aria-label={`Edit life area: ${area.name}`}
                    style={{
                      background: 'transparent', border: '1px solid #282a2d',
                      color: 'var(--qc-gold, #fbbf24)', cursor: 'pointer', borderRadius: 6,
                      padding: '4px 8px', fontSize: 13, minHeight: 30,
                    }}
                  >
                    ✎
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
