import { useState } from 'react';

interface SettingsModalProps {
  focusMinutes: number;
  breakMinutes: number;
  onSave: (settings: { focusMinutes: number; breakMinutes: number }) => void;
  onClose: () => void;
}

/** Settings modal for pomodoro timer durations */
export const SettingsModal = ({ focusMinutes, breakMinutes, onSave, onClose }: SettingsModalProps) => {
  const [focus, setFocus] = useState(String(focusMinutes));
  const [brk, setBrk] = useState(String(breakMinutes));

  const handleSave = () => {
    const f = Math.max(1, Math.min(120, Number(focus) || 25));
    const b = Math.max(1, Math.min(30, Number(brk) || 5));
    onSave({ focusMinutes: f, breakMinutes: b });
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">Timer Settings</h3>
        <label className="modal-field">
          <span>Focus duration (min)</span>
          <input type="number" value={focus} onChange={(e) => setFocus(e.target.value)} min={1} max={120} />
        </label>
        <label className="modal-field">
          <span>Break duration (min)</span>
          <input type="number" value={brk} onChange={(e) => setBrk(e.target.value)} min={1} max={30} />
        </label>
        <div className="modal-actions">
          <button className="badge badge-info" style={{ cursor: 'pointer', border: 'none', padding: '0.4rem 1rem' }} onClick={onClose}>Cancel</button>
          <button className="badge badge-success" style={{ cursor: 'pointer', border: 'none', padding: '0.4rem 1rem' }} onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
};
