import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { Habit, HabitStats } from '../services/api';

export const HabitReport = () => {
  const { habitId } = useParams<{ habitId: string }>();
  const navigate = useNavigate();
  const [habit, setHabit] = useState<Habit | null>(null);
  const [allHabits, setAllHabits] = useState<Habit[]>([]);
  const [stats, setStats] = useState<HabitStats | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!habitId) {
      endpoints.habits.list().then((h) => {
        setAllHabits(h);
        setLoaded(true);
      });
      return;
    }
    const id = Number(habitId);
    endpoints.habits.list().then((h) => setHabit(h.find((x) => x.id === id) ?? null));
    endpoints.habits.stats(id).then(setStats).catch(() => {});
  }, [habitId]);

  // No habit selected → show a picker (nav link /habit-report).
  if (!habitId) {
    if (!loaded) return <div className="vault-muted">Loading…</div>;
    return (
      <div>
        <Header title="Habit Report" />
        <div className="card-grid">
          {allHabits.length === 0 && <div className="vault-muted">No habits yet.</div>}
          {allHabits.map((h) => (
            <button
              key={h.id}
              className="card"
              style={{ textAlign: 'left', cursor: 'pointer', color: 'var(--text-primary)' }}
              onClick={() => navigate(`/habits/${h.id}/report`)}
            >
              <div style={{ fontWeight: 600 }}>{h.name}</div>
              <div className="vault-muted">Current streak: {h.current_streak}d · View report →</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (!habit) return <div className="vault-muted">Loading…</div>;

  const graphData = stats?.streak_graph ?? [];

  return (
    <div>
      <Header title={habit.name} />
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div>
            <div className="label">Records this month</div>
            <div className="value">{stats?.records_this_month ?? 0}</div>
          </div>
          <div>
            <div className="label">Days missed</div>
            <div className="value">{stats?.days_missed ?? 0}</div>
          </div>
          <div>
            <div className="label">Current streak</div>
            <div className="value">{habit.current_streak}d</div>
          </div>
          <div>
            <div className="label">Longest streak</div>
            <div className="value">{habit.longest_streak}d</div>
          </div>
          {stats?.is_new_record && (
            <div style={{ color: 'var(--habit-red)', fontWeight: 700, fontSize: 13 }}>
              🏆 New record!
            </div>
          )}
        </div>
      </div>

      {graphData.length > 0 && (
        <div className="card">
          <div className="vault-heading" style={{ marginBottom: 8 }}>30-Day Streak Graph</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={graphData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--vault-border)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: 'var(--vault-text-muted)' }}
                tickFormatter={(d) => d.slice(5)}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'var(--vault-text-muted)' }}
                width={36}
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--vault-bg-card)',
                  border: '1px solid var(--vault-border)',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="streak_length"
                stroke="var(--habit-blue)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <button
        className="btn-complete"
        style={{ marginTop: 12 }}
        onClick={() => navigate('/habits')}
      >
        Back to Habits
      </button>
    </div>
  );
};
