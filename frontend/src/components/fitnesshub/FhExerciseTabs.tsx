import { useState } from 'react';
import type { Exercise, MuscleGroupOverview } from '../../services/api';

interface Props {
  groups: MuscleGroupOverview[];
  allExercises: Exercise[];
  exerciseByGroup: Record<number, Exercise[]>;
}

/** Row 5: Exercises (Phases 94-95, 97) — By Muscle group / All Exercises tabs. */
export const FhExerciseTabs = ({ groups, allExercises, exerciseByGroup }: Props) => {
  const [tab, setTab] = useState<'by-muscle' | 'all'>('by-muscle');

  return (
    <section className="fh-row" id="exercises">
      <div className="fh-row-head">
        <div>
          <div className="fh-section-title">Row 5 · Exercises</div>
          <div className="fh-tabs" role="tablist" aria-label="Exercise view">
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'by-muscle'}
              className={`fh-tab${tab === 'by-muscle' ? ' active' : ''}`}
              onClick={() => setTab('by-muscle')}
            >
              By Muscle group
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'all'}
              className={`fh-tab${tab === 'all' ? ' active' : ''}`}
              onClick={() => setTab('all')}
            >
              All Exercises
            </button>
          </div>
        </div>
      </div>

      {tab === 'by-muscle' ? (
        <div className="fh-exercise-grid">
          {groups.length === 0 && (
            <div className="fh-empty" style={{ gridColumn: '1 / -1' }}>
              <span className="fh-empty-icon" aria-hidden="true">🏋️</span>
              <span className="fh-empty-title">No muscle groups</span>
              <span>Seed muscle groups to browse exercises by target area.</span>
            </div>
          )}
          {groups.map((g) => {
            const list = exerciseByGroup[g.id] ?? [];
            return (
              <div key={g.id} className="fh-exercise-card">
                <div className="fh-exercise-head">
                  <span className="fh-exercise-name">{g.name}</span>
                  <span className={`fh-body-badge ${g.body_part.toLowerCase()}`}>{g.body_part}</span>
                </div>
                {list.length === 0 ? (
                  <div className="fh-exercise-group">No exercises yet.</div>
                ) : (
                  <ul className="fh-set-list">
                    {list.map((ex) => (
                      <li key={ex.id}>
                        <span className="fh-set-label">{ex.name}</span>
                        <span className="fh-set-weight">
                          {Array.from({ length: ex.sets }).map((_, si) => `Set ${si + 1}: ${ex.weight}kg`).join(' · ')}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="fh-exercise-grid">
          {allExercises.length === 0 && (
            <div className="fh-empty" style={{ gridColumn: '1 / -1' }}>
              <span className="fh-empty-icon" aria-hidden="true">🏋️</span>
              <span className="fh-empty-title">No exercises</span>
              <span>Add exercises via Quick-Action to populate this grid.</span>
            </div>
          )}
          {allExercises.map((ex) => {
            const group = groups.find((g) => g.id === ex.muscle_group_id);
            return (
              <div key={ex.id} className="fh-exercise-card">
                <div className="fh-exercise-head">
                  <span className="fh-exercise-name">{ex.name}</span>
                  {group && <span className="fh-exercise-group">{group.name}</span>}
                </div>
                <ul className="fh-set-list">
                  {Array.from({ length: ex.sets }).map((_, si) => (
                    <li key={si}>
                      <span className="fh-set-label">Set {si + 1}</span>
                      <span className="fh-set-weight">
                        {ex.reps} reps @ {ex.weight}kg
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
