import type { LifePlannerEvent, Reminder, Task } from '../../services/api';
import { formatTime } from '../../utils/formatters';

interface QuickTaskManagerProps {
  reminders: Reminder[];
  todos: Task[];
  events: LifePlannerEvent[];
  onToggleReminder: (r: Reminder) => void;
  onToggleTodo: (t: Task) => void;
  onToggleEvent: (e: LifePlannerEvent) => void;
}

/** Middle row: three horizontal cards — Reminders, Mini To-Do, Events. */
export const QuickTaskManager = ({
  reminders, todos, events,
  onToggleReminder, onToggleTodo, onToggleEvent,
}: QuickTaskManagerProps) => (
  <div className="quick-task-manager">
    <div className="card quick-task-card">
      <div className="qtc-title">⏰ Reminders</div>
      {reminders.length === 0 && <div className="reminders-empty">No reminders</div>}
      <div className="reminders-list">
        {reminders.slice(0, 5).map((r) => (
          <label key={r.id} className="reminder-row" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={r.is_completed}
              onChange={() => onToggleReminder(r)}
              className="todo-checkbox"
              aria-label={`Toggle reminder ${r.title}`}
            />
            <div className="reminder-body">
              <div className="reminder-title" style={{ textDecoration: r.is_completed ? 'line-through' : 'none' }}>
                {r.title}
              </div>
              {r.time && <div className="reminder-meta">at {formatTime(r.time)}</div>}
            </div>
          </label>
        ))}
      </div>
    </div>

    <div className="card quick-task-card">
      <div className="qtc-title">✅ Mini To-Do</div>
      {todos.length === 0 && <div className="mini-todo-empty">No tasks</div>}
      <div className="mini-todo">
        {todos.slice(0, 5).map((t) => (
          <label key={t.id} className="todo-row">
            <input
              type="checkbox"
              checked={t.status === 'Completed'}
              onChange={() => onToggleTodo(t)}
              className="todo-checkbox"
              aria-label={`Toggle task ${t.title}`}
            />
            <span className={`todo-text${t.status === 'Completed' ? ' done' : ''}`}>{t.title}</span>
          </label>
        ))}
      </div>
    </div>

    <div className="card quick-task-card">
      <div className="qtc-title">📅 Today's Events</div>
      {events.length === 0 && <div className="reminders-empty">No events today</div>}
      <div className="reminders-list">
        {events.slice(0, 5).map((e) => (
          <label key={e.id} className="reminder-row" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={e.is_completed}
              onChange={() => onToggleEvent(e)}
              className="todo-checkbox"
              aria-label={`Toggle event ${e.title}`}
            />
            <div className="reminder-body">
              <div className="reminder-title" style={{ textDecoration: e.is_completed ? 'line-through' : 'none' }}>
                {e.title}
              </div>
              <div className="reminder-meta">
                {e.time && <span>{formatTime(e.time)}</span>}
                {e.location && <span>· {e.location}</span>}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  </div>
);
