import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { confirmDelete } from '../utils/confirm';
import { SkeletonCard } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { Goal } from '../services/api';

export const Goals = () => {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [quarter, setQuarter] = useState('Q1');
  const [year, setYear] = useState(new Date().getFullYear());
  const [habitId, setHabitId] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    endpoints.goals.list()
      .then(setGoals)
      .catch(() => setError('Could not load goals — is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!title.trim() || saving) return;
    setSaving(true);
    try {
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
      setShowForm(false);
      load();
    } catch {
      setError('Could not create the goal');
    } finally {
      setSaving(false);
    }
  };

  // Defect #52: completing a goal is also written into the vault's day note
  // (POST /api/kb/reflections appends under "Reflections" in
  // second_brain/daily-life/YYYY-MM-DD.md). Best-effort: a vault without a
  // reachable daily-life folder still completes the goal.
  const toggleComplete = (g: Goal) => {
    endpoints.goals.complete(g.id)
      .then(() => {
        setError(null);
        if (!g.is_completed) {
          endpoints.kb.reflections
            .create({ content: `Goal achieved: ${g.title}`, kind: 'goal' })
            .catch(() => {});
        }
        load();
      })
      .catch(() => setError('Could not complete the goal'));
  };

  const remove = (id: number) => {
    if (!confirmDelete('this goal')) return;
    endpoints.goals.delete(id).then(load).catch(() => setError('Could not delete the goal'));
  };

  // Defect #49 fix: inline progress update.
  const setProgress = (g: Goal, pct: number) => {
    const clamped = Math.max(0, Math.min(100, Math.round(pct)));
    endpoints.goals.update(g.id, { progress_percentage: clamped })
      .then(load)
      .catch(() => setError('Could not update progress'));
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

      {error && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="card-grid">
        {loading ? (
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : goals.length === 0 ? (
          <EmptyState
            icon="🎯"
            title="No goals yet"
            message="Set a quarterly goal to track what matters."
            action={<button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>+ New Goal</button>}
          />
        ) : goals.map((g) => (
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
            {/* Defect #49 fix: progress stepper. */}
            {!g.is_completed && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.25rem', marginTop: '0.4rem' }}>
                <button className="btn btn-ghost btn-sm" onClick={() => setProgress(g, g.progress_percentage - 10)} aria-label="Decrease progress">−10%</button>
                <button className="btn btn-ghost btn-sm" onClick={() => setProgress(g, g.progress_percentage + 10)} aria-label="Increase progress">+10%</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
