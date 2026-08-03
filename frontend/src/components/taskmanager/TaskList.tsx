import { useState } from 'react';
import { endpoints } from '../../services/api';
import type { Task } from '../../services/api';
import { relativeDate, getPriorityColor } from '../../utils/formatters';

interface TaskListProps {
  tasks: Task[];
  onRefresh: () => void;
}

/** Enhanced task list with inline add form and optimistic status toggle */
export const TaskList = ({ tasks, onRefresh }: TaskListProps) => {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [subject, setSubject] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async () => {
    if (!title.trim() || submitting) return;
    setSubmitting(true);
    try {
      await endpoints.tasks.create({
        title: title.trim(),
        priority_tag: priority,
        subject_tag: subject || undefined,
        status: 'Not started',
        user_id: 1,
      });
      setTitle('');
      setPriority('Medium');
      setSubject('');
      setShowForm(false);
      onRefresh();
    } catch { /* ignore */ }
    setSubmitting(false);
  };

  const handleToggle = async (task: Task) => {
    const newStatus = task.status === 'Completed' ? 'Not started' : 'Completed';
    try {
      await endpoints.tasks.update(task.id, { status: newStatus });
      onRefresh();
    } catch { /* ignore */ }
  };

  const active = tasks.filter((t) => t.status !== 'Completed');
  const done = tasks.filter((t) => t.status === 'Completed');

  return (
    <div className="enhanced-task-list">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{active.length} pending</span>
        <button
          className="badge badge-info"
          style={{ cursor: 'pointer', border: 'none', padding: '0.3rem 0.75rem' }}
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? '− Cancel' : '+ Add'}
        </button>
      </div>

      {showForm && (
        <div className="task-add-form" style={{ marginBottom: '1rem' }}>
          <input
            placeholder="Task title…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
            <input
              placeholder="Subject tag"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              style={{ flex: 1 }}
            />
            <button
              className="badge badge-success"
              style={{ cursor: 'pointer', border: 'none', padding: '0.3rem 0.75rem' }}
              onClick={handleCreate}
            >
              Save
            </button>
          </div>
        </div>
      )}

      <div className="task-list-items">
        {active.map((t) => (
          <TaskRow key={t.id} task={t} onToggle={handleToggle} onRefresh={onRefresh} />
        ))}
      </div>

      {done.length > 0 && (
        <details className="task-done-section" style={{ marginTop: '0.75rem' }}>
          <summary style={{ fontSize: '0.75rem', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem 0' }}>
            Completed ({done.length})
          </summary>
          <div className="task-list-items">
            {done.map((t) => (
              <TaskRow key={t.id} task={t} onToggle={handleToggle} onRefresh={onRefresh} />
            ))}
          </div>
        </details>
      )}

      {!tasks.length && (
        <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No tasks yet. Click "+ Add" to create one.
        </div>
      )}
    </div>
  );
};

/* ── Single task row ── */

interface TaskRowProps {
  task: Task;
  onToggle: (task: Task) => void;
  onRefresh: () => void;
}

const TaskRow = ({ task, onToggle, onRefresh }: TaskRowProps) => (
  <label className="task-row" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 0', cursor: 'pointer' }}>
    <input
      type="checkbox"
      checked={task.status === 'Completed'}
      onChange={() => onToggle(task)}
      className="todo-checkbox"
    />
    <span style={{
      flex: 1,
      fontSize: '0.875rem',
      color: task.status === 'Completed' ? 'var(--text-muted)' : 'var(--text-primary)',
      textDecoration: task.status === 'Completed' ? 'line-through' : 'none',
    }}>
      {task.title}
    </span>
    {task.priority_tag && (
      <span style={{ fontSize: '0.6rem', fontWeight: 600, color: getPriorityColor(task.priority_tag) }}>
        {task.priority_tag}
      </span>
    )}
    {task.due_date && (
      <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
        {relativeDate(task.due_date)}
      </span>
    )}
    <button
      onClick={(e) => { e.preventDefault(); endpoints.tasks.delete(task.id).then(onRefresh); }}
      style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.75rem', opacity: 0.6 }}
      title="Delete"
    >✕</button>
  </label>
);
