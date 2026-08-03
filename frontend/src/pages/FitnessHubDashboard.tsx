import { useEffect, useRef, useState } from 'react';
import { endpoints } from '../services/api';
import { useFitnessHubData } from '../hooks/useFitnessHubData';
import {
  FhHeader,
  FhQuickActions,
  FhNavigation,
  FhWeightGoal,
  FhPRTracker,
  FhMembership,
  FhDietPlan,
  FhCreateModal,
  FhWeeklySplit,
  FhHabitHeatmaps,
  FhMuscleGroupGrid,
  FhExpenseCards,
  FhExerciseTabs,
} from '../components/fitnesshub';
import type { FhQuickActionKind } from '../components/fitnesshub/FhQuickActions';

/**
 * Fitness Hub dashboard (spec): fixed-sidebar layout — minimal header, six
 * sidebar modules (Quick-Action / Navigation / Weight Goal / PR-Tracker /
 * Membership / Diet-Plan) and five main rows (Weekly-Split / Habit-Tracking
 * heatmaps / Muscle-Group 3D grid / Expenses / Exercises).
 */
export const FitnessHubDashboard = () => {
  const { data, loading, errors, refresh } = useFitnessHubData();
  const [modalKind, setModalKind] = useState<FhQuickActionKind | null>(null);
  const appliedTheme = useRef(false);

  useEffect(() => {
    if (appliedTheme.current) return;
    appliedTheme.current = true;
    const root = document.getElementById('fitness-hub-root');
    if (root) root.setAttribute('data-theme', 'fitness-hub');
  }, []);

  const handleChanged = () => {
    void refresh();
  };

  const summary = data.summary;
  const totalCalories = data.workouts.reduce((s, w) => s + (w.calories ?? 0), 0);
  const activePlans = data.dietPlans.filter((p) => p.is_active).length;

  return (
    <div id="fitness-hub-root">
      <FhHeader
        workoutCount={data.workouts.length}
        totalCalories={totalCalories}
        activePlans={activePlans}
      />

      {errors.length > 0 && (
        <div className="fh-card" style={{ marginBottom: '1rem', borderColor: 'var(--fh-red)' }}>
          <span style={{ color: 'var(--fh-red)', fontSize: '0.78rem' }}>
            Some widgets failed to load: {errors.join(', ')}
          </span>
        </div>
      )}

      <div className="fh-layout">
        <aside className="fh-sidebar">
          {loading && !data.summary ? (
            <>
              <div className="fh-skeleton fh-skeleton-sidebar" />
              <div className="fh-skeleton fh-skeleton-sidebar" />
              <div className="fh-skeleton fh-skeleton-sidebar" style={{ height: 120 }} />
            </>
          ) : (
            <>
              <FhQuickActions onCreate={setModalKind} />
              <FhNavigation />
              <FhWeightGoal
                weightGoal={summary?.weight_goal ?? null}
                onEdit={() => setModalKind('weight-goal')}
              />
              <FhPRTracker records={summary?.pr_tracker ?? []} />
              <FhMembership membership={summary?.membership ?? null} />
              <FhDietPlan plans={data.dietPlans} />
            </>
          )}
        </aside>

        <div className="fh-main">
          {/* ── Row 1: Weekly Split (Phases 73-79) ── */}
          {loading && !data.summary ? (
            <div className="fh-skeleton fh-skeleton-card" />
          ) : (
            <FhWeeklySplit
              week1={summary?.weekly_split?.[1] ?? []}
              week2={summary?.weekly_split?.[2] ?? []}
              workouts={data.workouts}
              onWorkoutLogged={handleChanged}
            />
          )}

          {/* ── Row 2: Habit-Tracking heatmaps (Phases 80-86) ── */}
          {loading && !data.summary ? (
            <div className="fh-skeleton fh-skeleton-heat" />
          ) : (
            <FhHabitHeatmaps habits={summary?.spec_habits ?? []} onChanged={handleChanged} />
          )}

          {/* ── Row 3: Muscle-Group 3D grid (Phases 87-91) ── */}
          {loading && !data.summary ? (
            <div className="fh-skeleton fh-skeleton-card" />
          ) : (
            <FhMuscleGroupGrid groups={summary?.muscle_groups ?? []} />
          )}

          {/* ── Row 4: Expenses + donut (Phases 92-93, 96) ── */}
          {loading && !data.summary ? (
            <div className="fh-skeleton fh-skeleton-card" />
          ) : (
            <FhExpenseCards
              expenses={data.expenses}
              summary={summary?.expenses_summary ?? { total: 0, by_category: {} }}
              onDelete={async (id) => {
                await endpoints.fitnessHub.deleteExpense(id);
                handleChanged();
              }}
            />
          )}

          {/* ── Row 5: Exercises (Phases 94-95, 97) ── */}
          {loading && !data.summary ? (
            <div className="fh-skeleton fh-skeleton-card" />
          ) : (
            <FhExerciseTabs
              groups={summary?.muscle_groups ?? []}
              allExercises={data.allExercises}
              exerciseByGroup={data.exerciseByGroup}
            />
          )}
        </div>
      </div>

      {modalKind && (
        <FhCreateModal kind={modalKind} onClose={() => setModalKind(null)} onCreated={handleChanged} />
      )}
    </div>
  );
};
