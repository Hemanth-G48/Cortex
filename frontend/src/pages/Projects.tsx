import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { Project } from '../services/api';

export const Projects = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form, setForm] = useState({ name: '', description: '', status: 'Not started', deadline: '' });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.projects.list()
      .then(setProjects)
      // Defect #28 fix: surface load failures.
      .catch(() => setError('Could not load projects — is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', description: '', status: 'Not started', deadline: '' });
    setShowForm(true);
  };

  const openEdit = (p: Project) => {
    setEditing(p);
    setForm({
      name: p.name,
      description: p.description ?? '',
      status: p.status ?? 'Not started',
      deadline: p.deadline ?? '',
    });
    setShowForm(true);
  };

  // Defect #26 fix: create/edit/delete from this page.
  const handleSave = async () => {
    if (!form.name.trim()) return;
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description || null,
        status: form.status,
        deadline: form.deadline || null,
      };
      if (editing) await endpoints.projects.update(editing.id, payload);
      else await endpoints.projects.create(payload);
      setShowForm(false);
      load();
    } catch {
      setError('Could not save the project');
    }
  };

  const handleDelete = (id: number) => {
    if (!confirmDelete('this project')) return;
    endpoints.projects.delete(id).then(load).catch(() => setError('Could not delete project'));
  };

  return (
    <div>
      <Header title="Project Planner" />
      <div style={{ marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={openCreate}>+ New Project</button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <h3 style={{ margin: 0 }}>{editing ? 'Edit Project' : 'New Project'}</h3>
          <input placeholder="Project name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} style={{ width: 'auto' }}>
              <option>Not started</option>
              <option>In progress</option>
              <option>Completed</option>
            </select>
            <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} style={{ width: 180 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleSave()} disabled={!form.name.trim()}>
              {editing ? 'Save Changes' : 'Create'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total Projects</div><div className="value">{projects.length}</div></div>
        <div className="stat-tile"><div className="label">Active</div><div className="value">{projects.filter((p) => p.status !== 'Completed').length}</div></div>
      </div>
      <div className="card-grid">
        {loading ? (
          // Defect #28 fix: skeletons while loading.
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : projects.length === 0 ? (
          <EmptyState
            icon="📁"
            title="No projects yet"
            message="Create a project to start organizing your work."
            action={<button type="button" className="btn btn-primary" onClick={openCreate}>+ New Project</button>}
          />
        ) : projects.map((p) => (
          <div className="card" key={p.id}>
            {/* Defect #27 fix: card links to project detail. */}
            <Link to={`/vault`} state={{ projectId: p.id }} style={{ textDecoration: 'none', color: 'inherit' }}>
              <h3 style={{ marginBottom: '0.25rem' }}>{p.name}</h3>
            </Link>
            {p.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{p.description}</p>}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }}>
              <span className={`badge badge-${p.status === 'Completed' ? 'success' : p.status === 'In progress' ? 'warning' : 'info'}`}>{p.status}</span>
              {p.deadline && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Deadline: {p.deadline}</span>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button onClick={() => openEdit(p)} style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.75rem' }}>Edit</button>
              <button onClick={() => handleDelete(p.id)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.75rem' }}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
