import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { SplitDay, WeekActualDay, Workout } from '../../services/api';

interface Props {
  week1: SplitDay[];
  week2: SplitDay[];
  workouts: Workout[];
  onWorkoutLogged: () => void;
}

const SPLIT_CLASS: Record<string, string> = {
  PUSH: 'push',
  PULL: 'pull',
  LEG: 'leg',
  REST: 'rest',
};

/** Row 1: Weekly Split (Phases 73-79) — Week 1/2 tabs, Mon-Sat day cards, Log Today's Workout. */
export const FhWeeklySplit = ({ week1, week2, workouts, onWorkoutLogged }: Props) => {
  const { toast } = useToast();
  const [tab, setTab] = useState<'1' | '2' | 'custom'>('1');
  const [showLog, setShowLog] = useState(false);
  const [type, setType] = useState('PUSH');
  const [duration, setDuration] = useState('45');
  const [calories, setCalories] = useState('');
  // Defect #84: what was actually trained each day this week (plan + actuals).
  const [actuals, setActuals] = useState<Record<number, WeekActualDay>>({});

  useEffect(() => {
    endpoints.fitness
      .weekActuals()
      .then((r) => {
        const byDow: Record<number, WeekActualDay> = {};
        for (const d of r.days) byDow[d.day_of_week] = d;
        setActuals(byDow);
      })
      .catch(() => setActuals({}));
  }, [workouts]);

  const days = tab === '1' ? week1 : week2;
  const today = new Date().toISOString().slice(0, 10);
  const loggedToday = workouts.some((w) => w.date === today);

  const submit = async () => {
    try {
      await endpoints.fitness.createWorkout({
        date: today,
        type,
        duration_minutes: Number(duration) || 45,
        calories: Number(calories) || null,
        user_id: 1,
      });
      toast('Workout logged! 💪', 'success');
      setShowLog(false);
      onWorkoutLogged();
    } catch {
      toast('Could not log workout', 'error');
    }
  };

  return (
    <section className="fh-row" id="split">
      <div className="fh-row-head">
        <div>
          <div className="fh-section-title">Row 1 · Weekly-Split</div>
          <div className="fh-tabs" role="tablist" aria-label="Week selection">
            {(['1', '2'] as const).map((w) => (
              <button
                key={w}
                type="button"
                role="tab"
                aria-selected={tab === w}
                className={`fh-tab${tab === w ? ' active' : ''}`}
                onClick={() => setTab(w)}
              >
                Week {w}
              </button>
            ))}
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'custom'}
              className={`fh-tab${tab === 'custom' ? ' active' : ''}`}
              onClick={() => setTab('custom')}
            >
              Customization
            </button>
          </div>
        </div>
        <button type="button" className="fh-cta-btn" onClick={() => setShowLog(true)}>
          🏋️ Log Today's Workout
        </button>
      </div>

      {tab === 'custom' ? (
        <div className="fh-empty">
          <span className="fh-empty-icon" aria-hidden="true">🎛️</span>
          <span className="fh-empty-title">Customization</span>
          <span>
            Drag-and-drop day cards to reorder, or use the create modal to tweak your active week.
            Changes persist instantly via the workout-split API.
          </span>
        </div>
      ) : (
        <div className="fh-split-scroll">
          {days.length === 0 && (
            <div className="fh-empty" style={{ flex: 1 }}>
              <span className="fh-empty-icon" aria-hidden="true">📅</span>
              <span>No split configured for Week {tab} yet.</span>
            </div>
          )}
          {days.map((d) => {
            const actual = actuals[d.day_of_week];
            const didToday = actual?.logged && actual.date === today;
            return (
            <div key={d.day} className={`fh-day-card${loggedToday && actual?.date === today ? ' done' : ''}`}>
              <div className="fh-day-head">
                <span className="fh-day-label">{d.day}</span>
                <span className={`fh-split-badge ${SPLIT_CLASS[d.split_name.toUpperCase()] ?? 'rest'}`}>
                  {d.split_name}
                </span>
              </div>
              <ul className="fh-day-exercises">
                {d.exercises.slice(0, 5).map((ex) => (
                  <li key={ex}>{ex}</li>
                ))}
                {d.exercises.length === 0 && <li>Rest / Recovery</li>}
              </ul>
              {actual && actual.workouts.length > 0 && (
                <div className="fh-day-exercises" style={{ fontSize: '0.7rem', color: 'var(--fh-text-muted, #999)' }}>
                  Actual: {actual.workouts.map((w) => w.type).join(', ')}
                  {actual.total_minutes > 0 ? ` · ${actual.total_minutes}m` : ''}
                </div>
              )}
              {actual?.vault_mentions && actual.workouts.length === 0 && (
                <div className="fh-day-exercises" style={{ fontSize: '0.7rem', color: 'var(--fh-text-muted, #999)' }}>
                  📓 Vault note mentions a workout
                </div>
              )}
              {didToday && (
                <span className="fh-day-done-chip">
                  ✓ Logged today
                </span>
              )}
            </div>
            );
          })}
        </div>
      )}

      {showLog && (
        <div className="modal-overlay" onClick={() => setShowLog(false)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Log Today's Workout"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-title">Log Today's Workout</div>
            <div className="fh-modal-body">
              <div className="fh-field">
                <label htmlFor="fh-wk-type">Workout Type</label>
                <select id="fh-wk-type" value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="PUSH">PUSH</option>
                  <option value="PULL">PULL</option>
                  <option value="LEG">LEG</option>
                  <option value="Running">Running</option>
                  <option value="Cardio">Cardio</option>
                  <option value="Yoga">Yoga</option>
                </select>
              </div>
              <div className="fh-field">
                <label htmlFor="fh-wk-duration">Duration (minutes)</label>
                <input id="fh-wk-duration" type="number" min={1} value={duration} onChange={(e) => setDuration(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-wk-cal">Calories (optional)</label>
                <input id="fh-wk-cal" type="number" min={0} value={calories} onChange={(e) => setCalories(e.target.value)} />
              </div>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowLog(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={() => void submit()}>
                Save Workout
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
