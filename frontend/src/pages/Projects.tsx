import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Project } from '../services/api';

export const Projects = () => {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => { endpoints.projects.list().then(setProjects).catch(() => {}); }, []);

  return (
    <div>
      <Header title="Project Planner" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total Projects</div><div className="value">{projects.length}</div></div>
        <div className="stat-tile"><div className="label">Active</div><div className="value">{projects.filter((p) => p.status !== 'Completed').length}</div></div>
      </div>
      <div className="card-grid">
        {projects.map((p) => (
          <div className="card" key={p.id}>
            <h3 style={{ marginBottom: '0.25rem' }}>{p.name}</h3>
            {p.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{p.description}</p>}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }}>
              <span className={`badge badge-${p.status === 'Completed' ? 'success' : p.status === 'In progress' ? 'warning' : 'info'}`}>{p.status}</span>
              {p.deadline && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Deadline: {p.deadline}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
