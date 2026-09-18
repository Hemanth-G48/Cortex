import { useEffect, useState, useCallback } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import { SkeletonCard, SkeletonTable } from '../components/shared/Skeleton';
import { EmptyState } from '../components/shared/EmptyState';
import type { Workout, FitnessGoal } from '../services/api';

export const Fitness = () => {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [goals, setGoals] = useState<FitnessGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWorkout, setShowWorkout] = useState(false);
  const [showGoal, setShowGoal] = useState(false);
  const [workoutForm, setWorkoutForm] = useState({ date: new Date().toISOString().split('T')[0], type: 'cardio', duration_minutes: 30, calories: 0 });
  const [goalForm, setGoalForm] = useState({ name: '', target: 10, unit: 'km', current: 0 });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      endpoints.fitness.workouts().catch(() => null),
      endpoints.fitness.goals().catch(() => null),
    ]).then(([w, g]) => {
      // Defect #33 fix: surface failures when both fetches fail.
      if (w === null && g === null) {
        setError('Could not load fitness data — is the backend running?');
        return;
      }
      setWorkouts(w ?? []);
      setGoals(g ?? []);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Defect #31 fix: workout logging from this page.
  const handleWorkout = async () => {
    try {
      await endpoints.fitness.createWorkout({
        date: workoutForm.date,
        type: workoutForm.type,
        duration_minutes: Number(workoutForm.duration_minutes) || 0,
        calories: Number(workoutForm.calories) || null,
      });
      setWorkoutForm({ date: new Date().toISOString().split('T')[0], type: 'cardio', duration_minutes: 30, calories: 0 });
      setShowWorkout(false);
      load();
    } catch {
      setError('Could not log the workout');
    }
  };

  // Defect #32 fix: goal creation from this page.
  const handleGoal = async () => {
    if (!goalForm.name.trim()) return;
    try {
      await endpoints.fitness.createGoal({
        name: goalForm.name.trim(),
        target: Number(goalForm.target) || 1,
        unit: goalForm.unit,
        current: Number(goalForm.current) || 0,
      });
      setGoalForm({ name: '', target: 10, unit: 'km', current: 0 });
      setShowGoal(false);
      load();
    } catch {
      setError('Could not create the goal');
    }
  };

  // Defect #85 fix: update goal progress.
  const updateGoalProgress = (g: FitnessGoal, current: number) => {
    endpoints.fitness.updateGoal(g.id, { current: Math.max(0, Math.min(current, g.target)) })
      .then(load)
      .catch(() => setError('Could not update goal progress'));
  };

  const totalMinutes = workouts.reduce((s, w) => s + w.duration_minutes, 0);
  const totalCalories = workouts.reduce((s, w) => s + (w.calories ?? 0), 0);

  return (
    <div>
      <Header title="Fitness Hub" />
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowWorkout(!showWorkout)}>
          {showWorkout ? '− Cancel' : '+ Log Workout'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => setShowGoal(!showGoal)}>
          {showGoal ? '− Cancel' : '+ New Goal'}
        </button>
      </div>

      {showWorkout && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input type="date" value={workoutForm.date} onChange={(e) => setWorkoutForm({ ...workoutForm, date: e.target.value })} style={{ width: 170 }} />
            <select value={workoutForm.type} onChange={(e) => setWorkoutForm({ ...workoutForm, type: e.target.value })} style={{ width: 'auto' }}>
              <option>cardio</option><option>strength</option><option>flexibility</option><option>sports</option>
            </select>
            <input type="number" placeholder="Minutes" value={workoutForm.duration_minutes} onChange={(e) => setWorkoutForm({ ...workoutForm, duration_minutes: Number(e.target.value) })} style={{ width: 110 }} />
            <input type="number" placeholder="Calories" value={workoutForm.calories} onChange={(e) => setWorkoutForm({ ...workoutForm, calories: Number(e.target.value) })} style={{ width: 110 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleWorkout()}>Log</button>
          </div>
        </div>
      )}

      {showGoal && (
        <div className="card" style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input placeholder="Goal name (e.g. Run 50km this month)" value={goalForm.name} onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <input type="number" placeholder="Target" value={goalForm.target} onChange={(e) => setGoalForm({ ...goalForm, target: Number(e.target.value) })} style={{ width: 110 }} />
            <input placeholder="Unit" value={goalForm.unit} onChange={(e) => setGoalForm({ ...goalForm, unit: e.target.value })} style={{ width: 90 }} />
            <input type="number" placeholder="Current" value={goalForm.current} onChange={(e) => setGoalForm({ ...goalForm, current: Number(e.target.value) })} style={{ width: 110 }} />
            <button type="button" className="btn btn-primary" onClick={() => void handleGoal()} disabled={!goalForm.name.trim()}>Create</button>
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--danger)' }}>
          <div style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>⚠ {error}</div>
          <button type="button" className="btn btn-primary" onClick={load}>Retry</button>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Workouts</div><div className="value">{workouts.length}</div></div>
        <div className="stat-tile"><div className="label">Total Minutes</div><div className="value">{totalMinutes}</div></div>
        <div className="stat-tile"><div className="label">Calories Burned</div><div className="value">{totalCalories}</div></div>
      </div>
      <div className="page-section">
        <h2>Fitness Goals</h2>
        <div className="card-grid">
          {loading ? (
            <><SkeletonCard /><SkeletonCard /></>
          ) : goals.length === 0 ? (
            <EmptyState
              icon="🏃"
              title="No fitness goals yet"
              message="Set a goal to track your progress over time."
              action={<button type="button" className="btn btn-primary" onClick={() => setShowGoal(true)}>+ New Goal</button>}
            />
          ) : goals.map((g) => (
            <div className="card" key={g.id}>
              <h3 style={{ marginBottom: '0.25rem' }}>{g.name}</h3>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                {g.current} / {g.target} {g.unit ?? ''}
              </div>
              <div className="xp-bar" style={{ width: '100%', height: '8px' }}>
                <div className="xp-fill" style={{ width: `${Math.min(100, (g.current / g.target) * 100)}%`, height: '8px' }} />
              </div>
              <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {Math.round((g.current / g.target) * 100)}%
              </div>
              {/* Defect #85 fix: inline progress stepper. */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Update progress:</span>
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => updateGoalProgress(g, g.current - 1)}
                    aria-label="Decrease progress"
                  >−</button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => updateGoalProgress(g, g.current + 1)}
                    aria-label="Increase progress"
                  >＋</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="page-section">
        <h2>Workout History</h2>
        <div className="card">
          {loading ? (
            SkeletonTable(4)
          ) : workouts.length === 0 ? (
            <EmptyState icon="💪" title="No workouts yet" message="Log your first workout to start tracking." />
          ) : (
            <table className="data-table">
              <thead><tr><th>Date</th><th>Type</th><th>Duration</th><th>Calories</th></tr></thead>
              <tbody>
                {workouts.map((w) => (
                  <tr key={w.id}>
                    <td>{w.date}</td>
                    <td>{w.type}</td>
                    <td>{w.duration_minutes}min</td>
                    <td>{w.calories ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
