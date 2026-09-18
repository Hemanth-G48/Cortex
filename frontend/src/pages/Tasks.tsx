import { useEffect, useMemo, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Task } from '../services/api';
import { TaskList } from '../components/taskmanager/TaskList';
import { SkeletonCard } from '../components/shared/Skeleton';
import type { MiniTodoItem } from '../components/taskmanager/MiniTodoList';

type VaultTask = MiniTodoItem;

export const Tasks = () => {
  const [dbTasks, setDbTasks] = useState<Task[]>([]);
  const [vaultTasks, setVaultTasks] = useState<VaultTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // DB tasks from /tasks
      const db = await endpoints.tasks.list();
      setDbTasks(db);
      // Defect #34 fix: also merge tasks parsed from second_brain/daily-life/*.md
      // via GET /api/kb/daily-notes?date=today (kb/daily_notes.py parser).
      const today = await endpoints.kb.dailyNotes.today().catch(() => null);
      const vault: VaultTask[] = (today?.documents ?? []).map((d) => ({
        id: `vault-${d.id}`,
        title: d.title ?? 'Untitled capture',
        subject_tag: null,
        priority_tag: d.quality_score === null ? null : 'Medium',
        priority_quadrant: null,
        due_date: null,
        status: 'In progress' as const,
        user_id: 1,
        project_id: null,
      }));
      setVaultTasks(vault);
    } catch {
      // Defect #7 fix: surface load failures instead of a silent empty table.
      setError('Could not load tasks — is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const merged = useMemo<VaultTask[]>(() => [...vaultTasks, ...dbTasks], [vaultTasks, dbTasks]);

  // Defect #8 fix: search + status/priority filters.
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return merged.filter((t) => {
      if (statusFilter === 'pending' && t.status === 'Completed') return false;
      if (statusFilter === 'completed' && t.status !== 'Completed') return false;
      if (priorityFilter !== 'all' && (t.priority_tag ?? '').toLowerCase() !== priorityFilter) return false;
      if (q && !t.title.toLowerCase().includes(q) && !(t.subject_tag ?? '').toLowerCase().includes(q)) return false;
      return true;
    });
  }, [merged, search, statusFilter, priorityFilter]);

  // Real DB tasks drive the editable list; vault captures render separately.
  const filteredDb = filtered.filter((t): t is Task => typeof t.id === 'number');
  const filteredVault = filtered.filter((t) => typeof t.id !== 'number');

  const pending = merged.filter((t) => t.status !== 'Completed').length;
  const completed = merged.filter((t) => t.status === 'Completed').length;

  return (
    <div>
      <Header title="Tasks" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Total</div><div className="value">{merged.length}</div></div>
        <div className="stat-tile"><div className="label">Pending</div><div className="value">{pending}</div></div>
        <div className="stat-tile"><div className="label">Completed</div><div className="value">{completed}</div></div>
      </div>

      {/* Defect #8 fix: search & filter controls. */}
      <div className="card" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 1rem' }}>
        <input
          placeholder="Search tasks…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: 180 }}
        />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ width: 'auto' }}>
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
        </select>
        <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} style={{ width: 'auto' }}>
          <option value="all">All priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={() => void load()}>Retry</button>
        </div>
      )}

      {vaultTasks.length > 0 && filteredVault.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            📥 Captured today from your vault (read-only — promote them to tasks from the Vault page)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {filteredVault.map((t) => (
              <div key={t.id} style={{ fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                <span>{t.title}</span>
                <span className="badge badge-info">{t.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        {loading ? (
          <div className="card-grid">
            <SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
        ) : (
          <TaskList tasks={filteredDb} onRefresh={load} />
        )}
      </div>
    </div>
  );
};
