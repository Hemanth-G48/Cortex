import type { Task } from '../../services/api';
import { EditIcon } from './EditIcon';

const STATUS_COLOR: Record<string, string> = {
  'Not started': 'var(--vault-text-muted)',
  'In progress': 'var(--habit-orange)',
  Completed: 'var(--success-teal)',
};

interface TaskCardProps {
  task: Task;
  /** Optional associated project name, shown under the title. */
  projectName?: string;
  /** Mark this task completed. */
  onComplete: (taskId: number) => void;
  /** Open the edit modal pre-filled for this task. */
  onEdit?: (task: Task) => void;
}

/** Vault-style task card: title, status tag, project name, edit pencil, mark-complete button. */
export const TaskCard = ({ task, projectName, onComplete, onEdit }: TaskCardProps) => {
  const done = task.status === 'Completed';
  return (
    <div className={`task-card${done ? ' done' : ''}`}>
      <div style={{ minWidth: 0 }}>
        <div className="task-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {task.title}
        </div>
        {projectName && (
          <div className="vault-muted" style={{ marginTop: 2 }}>{projectName}</div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {onEdit && <EditIcon onClick={() => onEdit(task)} title="Edit task" />}
        <span
          className="vault-muted"
          style={{
            border: '1px solid var(--vault-border)',
            borderRadius: 6,
            padding: '2px 8px',
            fontSize: 12,
            color: STATUS_COLOR[task.status] ?? 'var(--vault-text-muted)',
          }}
        >
          {task.status}
        </span>
        <button className={`btn-complete${done ? ' done' : ''}`} onClick={() => onComplete(task.id)} disabled={done}>
          {done ? 'Done' : 'Mark as completed'}
        </button>
      </div>
    </div>
  );
};
