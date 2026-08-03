import { useState } from 'react';
import type { Task } from '../../services/api';

interface MiniTodoListProps {
  tasks: Task[];
  onToggle?: (task: Task) => void;
}

/** Compact todo list with optimistic status toggle */
export const MiniTodoList = ({ tasks, onToggle }: MiniTodoListProps) => {
  const [optimisticIds, setOptimisticIds] = useState<Set<number>>(new Set());

  const handleToggle = (task: Task) => {
    setOptimisticIds((prev) => new Set(prev).add(task.id));
    onToggle?.(task);
    // Optimistic revert after a timeout if backend not available
    setTimeout(() => {
      setOptimisticIds((prev) => {
        const next = new Set(prev);
        next.delete(task.id);
        return next;
      });
    }, 2000);
  };

  const active = tasks.filter((t) => t.status !== 'Completed' && !optimisticIds.has(t.id));
  const done = tasks.filter((t) => t.status === 'Completed' || optimisticIds.has(t.id));

  if (!tasks.length) {
    return <div className="mini-todo-empty">No tasks yet</div>;
  }

  return (
    <div className="mini-todo">
      {active.slice(0, 5).map((t) => (
        <label key={t.id} className="todo-row">
          <input
            type="checkbox"
            checked={false}
            onChange={() => handleToggle(t)}
            className="todo-checkbox"
          />
          <span className="todo-text">{t.title}</span>
          {t.priority_tag && (
            <span className={`todo-priority priority-${t.priority_tag.toLowerCase()}`}>{t.priority_tag}</span>
          )}
        </label>
      ))}
      {done.length > 0 && (
        <details className="todo-done-section">
          <summary className="todo-done-summary">Completed ({done.length})</summary>
          {done.slice(0, 3).map((t) => (
            <label key={t.id} className="todo-row done">
              <input
                type="checkbox"
                checked={true}
                onChange={() => handleToggle(t)}
                className="todo-checkbox"
              />
              <span className="todo-text">{t.title}</span>
            </label>
          ))}
        </details>
      )}
    </div>
  );
};
