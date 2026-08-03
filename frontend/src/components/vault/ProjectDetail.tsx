import { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { endpoints, type ProjectTask } from '../../services/api';

interface ProjectDetailProps {
  projectId: number;
  onClose: () => void;
}

/** Drill-down view: list ProjectTasks, toggle completed, add new task. */
export const ProjectDetail = ({ projectId, onClose }: ProjectDetailProps) => {
  const { toast } = useToast();
  const [tasks, setTasks] = useState<ProjectTask[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    endpoints.projects.tasks(projectId).then(setTasks).finally(() => setLoading(false));
  };

  const toggle = (t: ProjectTask) => {
    endpoints.projects.updateTask(t.id, { completed: !t.completed, project_id: projectId })
      .then(() => { toast(t.completed ? 'Task reopened' : 'Task completed', 'success'); load(); })
      .catch(() => toast('Could not update task', 'error'));
  };

  const add = async () => {
    if (!newTitle.trim()) return;
    try {
      await endpoints.projects.createTask({ project_id: projectId, title: newTitle, completed: false });
      toast('Project task added', 'success');
      setNewTitle('');
      load();
    } catch {
      toast('Could not add task', 'error');
    }
  };

  return (
    <div className="vault-card" style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <div className="vault-heading">Project Tasks</div>
        <button className="btn-complete" onClick={onClose}>Close</button>
      </div>

      {loading && <div className="vault-muted">Loading…</div>}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
        {tasks.map((t) => (
          <label key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
            <input type="checkbox" checked={t.completed} onChange={() => toggle(t)} />
            <span style={{ textDecoration: t.completed ? 'line-through' : 'none', color: t.completed ? 'var(--vault-text-muted)' : 'var(--vault-text-primary)' }}>
              {t.title}
            </span>
          </label>
        ))}
        {tasks.length === 0 && !loading && <div className="vault-muted">No tasks yet.</div>}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="New task title"
          style={{
            flex: 1, background: 'var(--vault-bg-main)', border: '1px solid var(--vault-border)',
            borderRadius: 6, padding: '6px 10px', color: 'var(--vault-text-primary)', fontSize: 13,
          }}
          onKeyDown={(e) => e.key === 'Enter' && add()}
        />
        <button className="btn-complete" onClick={add} disabled={!newTitle.trim()}>Add</button>
      </div>
    </div>
  );
};
