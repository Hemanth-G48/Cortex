import { useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { SpecHabitHeatmap } from '../../services/api';

interface Props {
  habits: SpecHabitHeatmap[];
  onChanged: () => void;
}

const WEEKDAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/** Intensity level 1-4 for a heat cell (blue → green → yellow → red). */
function intensity(count: number, completed: boolean): number {
  if (!completed) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count <= 4) return 3;
  return 4;
}

/** Row 2: Habit-Tracking heatmaps (Phases 80-86) — 4 spec habits, 7x7 grids. */
export const FhHabitHeatmaps = ({ habits, onChanged }: Props) => {
  const { toast } = useToast();
  const [editingGoal, setEditingGoal] = useState<number | null>(null);
  const [goalDraft, setGoalDraft] = useState('');
  const [marking, setMarking] = useState<number | null>(null);

  if (habits.length === 0) {
    return (
      <section className="fh-row" id="habits">
        <div className="fh-section-title">Row 2 · Habit-Tracking</div>
        <div className="fh-empty">
          <span className="fh-empty-icon" aria-hidden="true">📊</span>
          <span className="fh-empty-title">No tracking habits</span>
          <span>Seed the 4 spec habits (Workout, 3000 Kcal, 4L water, Supplements) to see heatmaps.</span>
        </div>
      </section>
    );
  }

  const saveGoal = async (habitId: number) => {
    try {
      await endpoints.habits.setGoal(habitId, goalDraft.trim());
      toast('Goal updated ✅', 'success');
      setEditingGoal(null);
      onChanged();
    } catch {
      toast('Could not update goal', 'error');
    }
  };

  const markComplete = async (habitId: number) => {
    if (marking === habitId) return;
    setMarking(habitId);
    try {
      await endpoints.habits.logToday(habitId);
      toast('Marked as completed! 🎉', 'success');
      onChanged();
    } catch {
      toast('Could not log today', 'error');
    } finally {
      setMarking(null);
    }
  };

  return (
    <section className="fh-row" id="habits">
      <div className="fh-section-title">Row 2 · Habit-Tracking</div>
      <div className="fh-heat-grid">
        {habits.map((h) => {
          // Weak spots: weekday columns (Mon-Sun) whose fill % is lowest.
          const columnFill = WEEKDAY_ORDER.map((_, colIdx) => {
            let filled = 0;
            let total = 0;
            h.heatmap_7x7.forEach((cell, i) => {
              if (i % 7 === colIdx) {
                total += 1;
                if (cell.completed) filled += 1;
              }
            });
            return { col: colIdx, pct: total ? filled / total : 0 };
          });
          const minFill = Math.min(...columnFill.map((c) => c.pct));
          const weakCols = columnFill.filter((c) => c.pct === minFill && c.pct < 0.5);
          const weakLabels = weakCols.length > 0 && minFill < 0.5
            ? weakCols.map((c) => WEEKDAY_ORDER[c.col]).join(', ')
            : null;

          return (
            <div key={h.id} className="fh-heat-card">
              <div className="fh-heat-head">
                <div>
                  <div className="fh-heat-name">{h.name}</div>
                  {editingGoal === h.id ? (
                    <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center', marginTop: '0.3rem' }}>
                      <input
                        className="fh-goal-input"
                        value={goalDraft}
                        onChange={(e) => setGoalDraft(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void saveGoal(h.id);
                          if (e.key === 'Escape') setEditingGoal(null);
                        }}
                        autoFocus
                        aria-label={`Edit goal for ${h.name}`}
                      />
                      <button type="button" className="fh-goal-edit" onClick={() => void saveGoal(h.id)}>✓</button>
                    </div>
                  ) : (
                    <div className="fh-heat-goal">
                      <span>{h.goal ?? 'No goal set'}</span>
                      <button
                        type="button"
                        className="fh-goal-edit"
                        onClick={() => { setEditingGoal(h.id); setGoalDraft(h.goal ?? ''); }}
                        aria-label={`Edit goal for ${h.name}`}
                      >
                        ✏️
                      </button>
                    </div>
                  )}
                </div>
                <span className="fh-heat-percent">{h.percent}%</span>
              </div>

              <div className="fh-heat-stats">
                <span><b>{h.days_completed}</b> days completed</span>
                <span>Goal: <b>{h.goal ? 'daily' : '—'}</b></span>
              </div>

              <div className="fh-heat-cells" aria-label={`${h.name} 7-day heatmap`}>
                {h.heatmap_7x7.map((cell) => (
                  <div
                    key={cell.date}
                    className={`fh-heat-cell filled-${intensity(cell.count, cell.completed)}`}
                    title={`${cell.date}${cell.completed ? ' ✓' : ''}`}
                  />
                ))}
              </div>

              {weakLabels && (
                <div className="fh-weak-spot">⚠️ Weak spot: {weakLabels}</div>
              )}

              <button
                type="button"
                className="fh-mark-btn"
                disabled={marking === h.id}
                onClick={() => void markComplete(h.id)}
              >
                {marking === h.id ? '…' : '✓ Mark as completed'}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
};
