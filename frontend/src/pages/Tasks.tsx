import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Task } from '../services/api';
import { TaskList } from '../components/taskmanager/TaskList';

export const Tasks = () => {
  const [tasks, setTasks] = useState<Task[]>([]);

  const load = () => endpoints.tasks.list().then(setTasks).catch(() => {});

  useEffect(() => { load(); }, []);

  return (
    <div>
      <Header title="Tasks" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total</div><div className="value">{tasks.length}</div></div>
        <div className="stat-tile"><div className="label">Pending</div><div className="value">{tasks.filter((t) => t.status !== 'Completed').length}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{tasks.filter((t) => t.status === 'Completed').length}</div></div>
      </div>
      <div className="card">
        <TaskList tasks={tasks} onRefresh={load} />
      </div>
    </div>
  );
};
