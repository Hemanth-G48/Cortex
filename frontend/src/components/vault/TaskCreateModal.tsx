import { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { endpoints, type Project, type Task } from '../../services/api';

interface TaskCreateModalProps {
  /** Projects for the project-select dropdown. */
  projects: Project[];
  /** Existing task when editing (pre-fills the form). */
  task?: Task | null;
  onClose: () => void;
  onSaved: () => void;
}

/** Vault add/edit task modal: title, project select, priority, due date, status. */
export const TaskCreateModal = ({ projects, task, onClose, onSaved }: TaskCreateModalProps) => {
  const { toast } = useToast();
  const [title, setTitle] = useState(task?.title ?? '');
  const [projectId, setProjectId] = useState<number | ''>(task?.project_id ?? '');
  const [priority, setPriority] = useState(task?.priority_tag ?? '');
  const [dueDate, setDueDate] = useState(task?.due_date ?? '');
  const [status, setStatus] = useState(task?.status ?? 'Not started');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!title.trim() || saving) return;
    setSaving(true);
    try {
      if (task) {
        await endpoints.tasks.update(task.id, {
          title,
          project_id: projectId === '' ? null : Number(projectId),
          priority_tag: priority || null,
          due_date: dueDate || null,
          status,
        });
        toast('Task updated', 'success');
      } else {
        await endpoints.tasks.create({
          title,
          project_id: projectId === '' ? null : Number(projectId),
          priority_tag: priority || null,
          due_date: dueDate || null,
          status,
          user_id: 1,
        });
        toast('Task created', 'success');
      }
      onSaved();
    } catch {
      toast('Could not save task', 'error');
    } finally {
      setSaving(false);
    }
  };

  const field: React.CSSProperties = {
    width: '100%',
    background: 'var(--vault-bg-main)',
    border: '1px solid var(--vault-border)',
    borderRadius: 6,
    color: 'var(--vault-text-primary)',
    padding: '8px 10px',
    fontSize: 14,
    boxSizing: 'border-box',
  };
  const label: React.CSSProperties = { display: 'block', fontSize: 12, marginBottom: 4, color: 'var(--vault-text-muted)' };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        className="vault-card"
        style={{ width: 380, maxWidth: '92vw' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="vault-heading" style={{ marginBottom: 12 }}>{task ? 'Edit Task' : 'Add New Task'}</div>

        <label style={label}>Title</label>
        <input style={field} value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />

        <div style={{ marginTop: 10 }}>
          <label style={label}>Project (linked)</label>
          <select style={field} value={projectId} onChange={(e) => setProjectId(e.target.value === '' ? '' : Number(e.target.value))}>
            <option value="">— No project —</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div style={{ marginTop: 10 }}>
          <label style={label}>Priority</label>
          <select style={field} value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">None</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        <div style={{ marginTop: 10 }}>
          <label style={label}>Due date</label>
          <input type="date" style={field} value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </div>

        <div style={{ marginTop: 10 }}>
          <label style={label}>Status</label>
          <select style={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option>Not started</option>
            <option>In progress</option>
            <option>Completed</option>
          </select>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
          <button className="btn-complete" onClick={onClose}>Cancel</button>
          <button className="btn-complete" onClick={submit} disabled={!title.trim() || saving}>
            {saving ? 'Saving…' : task ? 'Save' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};
