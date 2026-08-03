import type { Project, ProjectSummary } from '../../services/api';
import { EditIcon } from './EditIcon';

const BADGE_COLOR: Record<string, string> = {
  Completed: 'var(--success-teal)',
  Overdue: 'var(--habit-red)',
  '7 Days to go': 'var(--habit-orange)',
  'No deadline': 'var(--vault-text-muted)',
};

interface ProjectCardProps {
  project: Project;
  summary: ProjectSummary;
  onEdit: (project: Project) => void;
  onDrill?: (project: Project) => void;
}

/** Vault-style project card: name, task counts, deadline badge, edit pencil, drill-down. */
export const ProjectCard = ({ project, summary, onEdit, onDrill }: ProjectCardProps) => (
  <div className="vault-card">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
      <div style={{ minWidth: 0 }}>
        <div
          className="vault-body"
          style={{
            fontWeight: 600,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            textDecoration: project.status === 'Completed' ? 'line-through' : 'none',
            color: project.status === 'Completed' ? 'var(--vault-text-muted)' : 'var(--vault-text-primary)',
          }}
        >
          {project.name}
        </div>
        <div className="vault-muted" style={{ marginTop: 4 }}>
          Total related tasks: {summary.total_tasks}
        </div>
        <div className="vault-muted">
          Total incomplete tasks: {summary.incomplete_tasks}
        </div>
      </div>
      <EditIcon onClick={() => onEdit(project)} title="Edit project" />
    </div>

    <div style={{ marginTop: 10 }}>
      <span
        style={{
          border: `1px solid ${BADGE_COLOR[summary.deadline_status] ?? 'var(--vault-border)'}`,
          color: BADGE_COLOR[summary.deadline_status] ?? 'var(--vault-text-primary)',
          borderRadius: 6,
          padding: '2px 8px',
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {summary.deadline_status}
      </span>
    </div>

    {onDrill && (
      <button
        aria-label="View project details"
        onClick={() => onDrill(project)}
        style={{
          marginTop: 8,
          background: 'none',
          border: '1px solid var(--vault-border)',
          borderRadius: 6,
          padding: '4px 10px',
          fontSize: 12,
          cursor: 'pointer',
          color: 'var(--vault-accent)',
        }}
      >
        View Tasks
      </button>
    )}
  </div>
);
