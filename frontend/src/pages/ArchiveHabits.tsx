import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { useToast } from '../hooks/useToast';
import { endpoints } from '../services/api';
import type { Habit } from '../services/api';

export const ArchiveHabits = () => {
  const { toast } = useToast();
  const [habits, setHabits] = useState<Habit[]>([]);

  const load = () => endpoints.habits.list(true).then(setHabits).catch(() => {});

  useEffect(() => { load(); }, []);

  const unarchive = (id: number) =>
    endpoints.habits.unarchive(id)
      .then(() => { toast('Habit restored to active', 'success'); load(); })
      .catch(() => toast('Could not unarchive habit', 'error'));

  const remove = (id: number) =>
    endpoints.habits.delete(id)
      .then(() => { toast('Habit deleted', 'info'); load(); })
      .catch(() => toast('Could not delete habit', 'error'));

  return (
    <div>
      <Header title="Archived Habits" />
      <div className="card-grid">
        {habits.length === 0 && <div className="vault-muted">No archived habits.</div>}
        {habits.map((h) => (
          <div className="card" key={h.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
              <h3 style={{ marginBottom: '0.25rem' }}>{h.name}</h3>
              <span className="vault-muted" style={{ fontSize: '0.75rem' }}>Archived</span>
            </div>
            {h.description && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{h.description}</p>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-complete" onClick={() => unarchive(h.id)}>Unarchive</button>
              <button className="btn-complete" onClick={() => remove(h.id)} style={{ background: 'var(--habit-red)', color: '#fff' }}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
