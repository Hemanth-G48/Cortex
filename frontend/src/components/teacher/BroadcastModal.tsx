import { useState, useCallback } from 'react';
import { teacherApi } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { BroadcastKind } from './BroadcastHub';

interface BroadcastModalProps {
  kind: BroadcastKind;
  selected: number[];
  onClose: () => void;
  onDone: () => void;
}

export const BroadcastModal = ({ kind, selected, onClose, onDone }: BroadcastModalProps) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [confirmAll, setConfirmAll] = useState(false);

  const isAll = selected.length === 0;
  const targetLabel = isAll ? 'ALL students' : `${selected.length} student${selected.length !== 1 ? 's' : ''} selected`;

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [status, setStatus] = useState('pending');
  const [priorityTag, setPriorityTag] = useState('Medium');
  const [currentAssignment, setCurrentAssignment] = useState('');
  const [totalAssignments, setTotalAssignments] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState('reading');
  const [date, setDate] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [activity, setActivity] = useState('');
  const [energy, setEnergy] = useState('Medium');
  const [location, setLocation] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const reset = () => {
    setTitle(''); setDescription(''); setDueDate(''); setStatus('pending');
    setPriorityTag('Medium'); setCurrentAssignment(''); setTotalAssignments('');
    setAuthor(''); setCategory('reading'); setDate(''); setTimeRange('');
    setActivity(''); setEnergy('Medium'); setLocation(''); setFile(null);
    setError(''); setConfirmAll(false);
  };

  const handleSubmit = useCallback(async () => {
    if (!title.trim()) { setError('Title is required.'); return; }
    setLoading(true);
    setError('');
    try {
      let result;
      switch (kind) {
        case 'course': {
          const ca = currentAssignment ? Number(currentAssignment) : undefined;
          const ta = totalAssignments ? Number(totalAssignments) : undefined;
          result = await teacherApi.broadcastCourses(
            { title: title.trim(), current_assignment: ca, total_assignments: ta },
            isAll ? undefined : selected,
          );
          break;
        }
        case 'assignment': {
          result = await teacherApi.broadcastAssignments(
            { title: title.trim(), description: description.trim() || undefined, due_date: dueDate || undefined, status },
            isAll ? undefined : selected,
            file,
          );
          break;
        }
        case 'todo': {
          result = await teacherApi.broadcastTodos(
            { title: title.trim(), due_date: dueDate || undefined, priority_tag: priorityTag },
            isAll ? undefined : selected,
          );
          break;
        }
        case 'book': {
          result = await teacherApi.broadcastBooks(
            { title: title.trim(), author: author.trim() || undefined, category },
            isAll ? undefined : selected,
            file,
          );
          break;
        }
        case 'schedule': {
          result = await teacherApi.broadcastSchedule(
            { date, time_range: timeRange.trim(), activity: activity.trim(), category, energy, location: location.trim() || null },
            isAll ? undefined : selected,
          );
          break;
        }
      }
      toast(`Broadcast complete — ${result.created} item${result.created !== 1 ? 's' : ''} created`, 'success');
      onDone();
      onClose();
      reset();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Broadcast failed');
    } finally {
      setLoading(false);
    }
  }, [kind, selected, isAll, title, description, dueDate, status, priorityTag, currentAssignment, totalAssignments, author, category, date, timeRange, activity, energy, location, file, toast, onDone, onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(520px, 92vw)' }}>
        <h2 className="modal-title">Broadcast {kind.charAt(0).toUpperCase() + kind.slice(1)}</h2>

        <div style={{ marginBottom: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Target: <strong>{targetLabel}</strong>
        </div>

        {isAll && !confirmAll && (
          <div className="card" style={{ padding: '0.75rem', marginBottom: '1rem', borderColor: 'var(--warning)', background: 'var(--warning-muted)' }}>
            <p style={{ fontSize: '0.8rem', margin: 0 }}>
              ⚠️ You are about to broadcast to <strong>ALL students</strong>. Are you sure?
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button type="button" className="btn btn-primary btn-sm" onClick={() => setConfirmAll(true)}>
                Confirm
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {isAll && confirmAll && (
          <div style={{ marginBottom: '1rem', fontSize: '0.8rem', color: 'var(--warning)' }}>
            Broadcasting to ALL students.
          </div>
        )}

        {error && (
          <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>{error}</div>
        )}

        {/* Course fields */}
        {kind === 'course' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Title</span>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Course name" />
            </label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Current assignment</label>
                <input className="form-input" type="number" min={0} value={currentAssignment} onChange={(e) => setCurrentAssignment(e.target.value)} placeholder="0" />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Total assignments</label>
                <input className="form-input" type="number" min={0} value={totalAssignments} onChange={(e) => setTotalAssignments(e.target.value)} placeholder="0" />
              </div>
            </div>
          </div>
        )}

        {/* Assignment fields */}
        {kind === 'assignment' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Title</span>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Assignment title" />
            </label>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Description</span>
              <textarea className="form-input" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Optional description" />
            </label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Due date</label>
                <input className="form-input" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Status</label>
                <select className="form-input" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="pending">Pending</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>
            </div>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>File (optional)</span>
              <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
          </div>
        )}

        {/* Todo fields */}
        {kind === 'todo' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Title</span>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Todo title" />
            </label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Priority</label>
                <select className="form-input" value={priorityTag} onChange={(e) => setPriorityTag(e.target.value)}>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Due date</label>
                <input className="form-input" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
            </div>
          </div>
        )}

        {/* Book fields */}
        {kind === 'book' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Title</span>
              <input className="form-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Book title" />
            </label>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Author</span>
              <input className="form-input" value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="Author name" />
            </label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Category</label>
                <select className="form-input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="reading">Reading</option>
                  <option value="finished">Finished</option>
                  <option value="want">Want</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>File (optional)</label>
                <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </div>
            </div>
          </div>
        )}

        {/* Schedule fields */}
        {kind === 'schedule' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Date</label>
                <input className="form-input" type="date" value={date || ''} onChange={(e) => setDate(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Time range</label>
                <input className="form-input" value={timeRange || ''} onChange={(e) => setTimeRange(e.target.value)} placeholder="09:00-10:00" />
              </div>
            </div>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Activity</span>
              <input className="form-input" value={activity} onChange={(e) => setActivity(e.target.value)} placeholder="e.g. Math lecture" />
            </label>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Category</label>
                <select className="form-input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="School">School</option>
                  <option value="Study Time">Study Time</option>
                  <option value="Break">Break</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Energy</label>
                <select className="form-input" value={energy} onChange={(e) => setEnergy(e.target.value)}>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
            </div>
            <label className="modal-field">
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600, display: 'block', marginBottom: '0.2rem' }}>Location (optional)</span>
              <input className="form-input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Room 101" />
            </label>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={() => void handleSubmit()} disabled={loading || (isAll && !confirmAll)}>
            {loading ? 'Broadcasting…' : 'Broadcast'}
          </button>
        </div>
      </div>
    </div>
  );
};
