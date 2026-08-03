import { useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Workout, FitnessGoal } from '../services/api';

export const Fitness = () => {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [goals, setGoals] = useState<FitnessGoal[]>([]);

  useEffect(() => {
    endpoints.fitness.workouts().then(setWorkouts).catch(() => {});
    endpoints.fitness.goals().then(setGoals).catch(() => {});
  }, []);

  const totalMinutes = workouts.reduce((s, w) => s + w.duration_minutes, 0);
  const totalCalories = workouts.reduce((s, w) => s + (w.calories ?? 0), 0);

  return (
    <div>
      <Header title="Fitness Hub" />
      <div className="stat-grid">
        <div className="stat-tile"><div className="label">Workouts</div><div className="value">{workouts.length}</div></div>
        <div className="stat-tile"><div className="label">Total Minutes</div><div className="value">{totalMinutes}</div></div>
        <div className="stat-tile"><div className="label">Calories Burned</div><div className="value">{totalCalories}</div></div>
      </div>
      <div className="page-section">
        <h2>Fitness Goals</h2>
        <div className="card-grid">
          {goals.map((g) => (
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
            </div>
          ))}
        </div>
      </div>
      <div className="page-section">
        <h2>Workout History</h2>
        <div className="card">
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
        </div>
      </div>
    </div>
  );
};
