import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import { MuscleDiagram } from './MuscleDiagram';
import type { Exercise, MuscleGroupOverview } from '../../services/api';

interface Props {
  groups: MuscleGroupOverview[];
}

/** Row 3: Muscle-Group 3D grid (Phases 87-91) — 12 cards, click to expand exercises. */
export const FhMuscleGroupGrid = ({ groups }: Props) => {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [exercises, setExercises] = useState<Record<number, Exercise[]>>({});

  useEffect(() => {
    if (expanded === null || exercises[expanded]) return;
    endpoints.fitnessHub.muscleGroupExercises(expanded)
      .then((ex) => setExercises((prev) => ({ ...prev, [expanded]: ex })))
      .catch(() => setExercises((prev) => ({ ...prev, [expanded]: [] })));
  }, [expanded, exercises]);

  if (groups.length === 0) {
    return (
      <section className="fh-row" id="muscles">
        <div className="fh-section-title">Row 3 · Muscle-Group</div>
        <div className="fh-empty">
          <span className="fh-empty-icon" aria-hidden="true">💪</span>
          <span className="fh-empty-title">No muscle groups</span>
          <span>Seed the 12 muscle groups to see the anatomical grid.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="fh-row" id="muscles">
      <div className="fh-section-title">Row 3 · Muscle-Group</div>
      <div className="fh-muscle-grid">
        {groups.map((g) => {
          const isOpen = expanded === g.id;
          const list = exercises[g.id] ?? [];
          return (
            <div
              key={g.id}
              className={`fh-muscle-card ${g.body_part.toLowerCase()}`}
              onClick={() => setExpanded(isOpen ? null : g.id)}
              role="button"
              tabIndex={0}
              aria-expanded={isOpen}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setExpanded(isOpen ? null : g.id);
                }
              }}
            >
              <div className="fh-muscle-svg-wrap" style={{ color: g.body_part === 'Lower' ? 'var(--fh-green)' : 'var(--fh-blue)' }}>
                <MuscleDiagram muscle={g.name} />
              </div>
              <div className="fh-muscle-name">{g.name}</div>
              <div className="fh-muscle-meta">
                <span className={`fh-body-badge ${g.body_part.toLowerCase()}`}>{g.body_part}</span>
                <span>Total Exercises: {g.exercise_count}</span>
              </div>

              {isOpen && (
                <div className="fh-muscle-expanded">
                  <div className="fh-expand-title">Exercises</div>
                  {list.length === 0 ? (
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>No exercises yet.</div>
                  ) : (
                    <ul className="fh-expand-list">
                      {list.map((ex) => (
                        <li key={ex.id}>
                          <span>{ex.name}</span>
                          <span className="fh-set-meta">{ex.sets}×{ex.reps} @ {ex.weight}kg</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};
