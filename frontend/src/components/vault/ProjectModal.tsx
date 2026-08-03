import { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { endpoints, type Project } from '../../services/api';

interface ProjectModalProps {
  /** Existing project when editing (pre-fills the form). */
  project?: Project | null;
  onClose: () => void;
  onSaved: () => void;
}

/** Vault add/edit project modal: name, description, status, deadline. */
export const ProjectModal = ({ project, onClose, onSaved }: ProjectModalProps) => {
  const { toast } = useToast();
  const [name, setName] = useState(project?.name ?? '');
  const [description, setDescription] = useState(project?.description ?? '');
  const [status, setStatus] = useState(project?.status ?? 'Not started');
  const [deadline, setDeadline] = useState(project?.deadline ?? '');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!name.trim() || saving) return;
    setSaving(true);
    try {
      if (project) {
        await endpoints.projects.update(project.id, {
          name,
          description: description || null,
          status,
          deadline: deadline || null,
          user_id: project.user_id,
        });
        toast('Project updated', 'success');
      } else {
        await endpoints.projects.create({
          name,
          description: description || null,
          status,
          deadline: deadline || null,
          user_id: 1,
        });
        toast('Project created', 'success');
      }
      onSaved();
    } catch {
      toast('Could not save project', 'error');
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
      <div className="vault-card" style={{ width: 380, maxWidth: '92vw' }} onClick={(e) => e.stopPropagation()}>
        <div className="vault-heading" style={{ marginBottom: 12 }}>{project ? 'Edit Project' : 'Add New Project'}</div>

        <label style={label}>Name</label>
        <input style={field} value={name} onChange={(e) => setName(e.target.value)} autoFocus />

        <div style={{ marginTop: 10 }}>
          <label style={label}>Description</label>
          <textarea style={{ ...field, minHeight: 60, resize: 'vertical' }} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div style={{ marginTop: 10 }}>
          <label style={label}>Status</label>
          <select style={field} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option>Not started</option>
            <option>In progress</option>
            <option>Completed</option>
          </select>
        </div>

        <div style={{ marginTop: 10 }}>
          <label style={label}>Deadline</label>
          <input type="date" style={field} value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
          <button className="btn-complete" onClick={onClose}>Cancel</button>
          <button className="btn-complete" onClick={submit} disabled={!name.trim() || saving}>
            {saving ? 'Saving…' : project ? 'Save' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};
