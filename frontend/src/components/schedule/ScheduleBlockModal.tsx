import { useState, useCallback } from 'react';
import type { DailyScheduleItem } from '../../services/api';

interface ScheduleBlockModalProps {
  open: boolean;
  initial: DailyScheduleItem | null;
  date: string;
  onClose: () => void;
  onSave: (data: {
    date: string;
    time_range: string;
    activity: string;
    category: 'School' | 'Study Time' | 'Break';
    location: string | null;
    energy: 'High' | 'Medium' | 'Low';
    notes: string | null;
  }) => void;
}

const TIME_RANGE_RE = /^\d{2}:\d{2}-\d{2}:\d{2}$/;

export const ScheduleBlockModal = ({ open, initial, date, onClose, onSave }: ScheduleBlockModalProps) => {
  const [timeRange, setTimeRange] = useState(initial?.time_range ?? '');
  const [activity, setActivity] = useState(initial?.activity ?? '');
  const [category, setCategory] = useState<DailyScheduleItem['category']>(initial?.category ?? 'School');
  const [energy, setEnergy] = useState<DailyScheduleItem['energy']>(initial?.energy ?? 'Medium');
  const [location, setLocation] = useState(initial?.location ?? '');
  const [notes, setNotes] = useState(initial?.notes ?? '');
  const [timeError, setTimeError] = useState('');

  const validateTime = useCallback((val: string) => {
    if (!TIME_RANGE_RE.test(val)) {
      setTimeError('Format must be HH:MM-HH:MM (e.g. 09:00-10:30)');
    } else {
      setTimeError('');
    }
  }, []);

  const handleTimeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setTimeRange(val);
      if (val) validateTime(val);
    },
    [validateTime],
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (timeRange && !TIME_RANGE_RE.test(timeRange)) {
        setTimeError('Format must be HH:MM-HH:MM (e.g. 09:00-10:30)');
        return;
      }
      onSave({
        date,
        time_range: timeRange,
        activity,
        category,
        location: location || null,
        energy,
        notes: notes || null,
      });
    },
    [date, timeRange, activity, category, location, energy, notes, onSave],
  );

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">{initial ? 'Edit Block' : 'Add Block'}</h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Date</label>
          <input type="date" value={date} onChange={() => {}} readOnly className="form-input" />

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Time Range</label>
          <input
            type="text"
            value={timeRange}
            onChange={handleTimeChange}
            placeholder="09:00-10:30"
            className="form-input"
            style={{ borderColor: timeError ? 'var(--danger)' : undefined }}
          />
          {timeError && <span style={{ fontSize: '0.7rem', color: 'var(--danger)' }}>{timeError}</span>}

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Activity</label>
          <input type="text" value={activity} onChange={(e) => setActivity(e.target.value)} placeholder="e.g. Math Lecture" className="form-input" />

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Category</label>
          <select value={category} onChange={(e) => setCategory(e.target.value as DailyScheduleItem['category'])} className="form-input">
            <option value="School">School</option>
            <option value="Study Time">Study Time</option>
            <option value="Break">Break</option>
          </select>

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Energy</label>
          <select value={energy} onChange={(e) => setEnergy(e.target.value as DailyScheduleItem['energy'])} className="form-input">
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Location</label>
          <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Room 204" className="form-input" />

          <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="form-input" style={{ resize: 'vertical' }} />

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">{initial ? 'Update' : 'Save'}</button>
          </div>
        </form>
      </div>
    </div>
  );
};
