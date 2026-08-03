import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Goal } from '../services/api';

export const Goals = () => {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(new Date().getFullYear());
  const [habitId, setHabitId] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [saving, setSaving] = useState(false);

  const load = () => endpoints.goals.list().then(setGoals).catch(() => {});

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!title.trim() || saving) return;
    setSaving(true);
    await endpoints.goals.create({
      title,
      quarter,
      year,
      habit_id: habitId ? Number(habitId) : null,
      target_date: targetDate || null,
      progress_percentage: 0,
      is_completed: false,
    });
    setTitle(''); setHabitId(''); setTargetDate('');
    setShowForm(false); setSaving(false);
    load();
  };

  const toggleComplete = (g: Goal) => {
    endpoints.goals.complete(g.id).then(load);
  };

  const remove = (id: number) => {
    endpoints.goals.delete(id).then(load);
  };

  return (
    <div>
      <Header title="Goals" />
      <div style={{ marginBottom: 12 }}>
        <button className="btn-complete" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Goal'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)}
            style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }} />
          <div style={{ display: 'flex', gap: 8 }}>
            <select value={quarter} onChange={(e) => setQuarter(e.target.value)}
              style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }}>
              <option>Q1</option><option>Q2</option><option>Q3</option><option>Q4</option>
            </select>
            <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} style={{ width: 70, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }} />
          </div>
          <input placeholder="Habit ID (optional)" value={habitId} onChange={(e) => setHabitId(e.target.value)}
            style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }} />
          <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)}
            style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--vault-border)', background: 'var(--vault-bg-main)', color: 'var(--vault-text-primary)' }} />
          <button className="btn-complete" onClick={create} disabled={!title.trim() || saving}>Create Goal</button>
        </div>
      )}

      <div className="card-grid">
        {goals.length === 0 && <div className="vault-muted">No goals yet.</div>}
        {goals.map((g) => (
          <div className="card" key={g.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
              <h3 style={{ textDecoration: g.is_completed ? 'line-through' : 'none' }}>{g.title}</h3>
              <button onClick={() => remove(g.id)} style={{ background: 'none', border: 'none', color: 'var(--habit-red)', cursor: 'pointer', fontSize: 14 }}>🗑</button>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--vault-text-muted)', marginBottom: 4 }}>
              {g.quarter} {g.year}{g.habit_id ? ` · Habit #${g.habit_id}` : ''}{g.target_date ? ` · Due ${g.target_date}` : ''}
            </div>
            <div className="xp-bar" style={{ width: '100%', height: 8, marginTop: '0.25rem' }}>
              <div className="xp-fill" style={{ width: `${g.progress_percentage}%`, height: 8 }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{g.progress_percentage}%</span>
              <button className="btn-complete" onClick={() => toggleComplete(g)} disabled={g.is_completed}>
                {g.is_completed ? '✓ Done' : 'Mark Complete'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
