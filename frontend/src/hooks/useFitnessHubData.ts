import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type {
  DietPlan,
  Exercise,
  Expense,
  FitnessHubSummary,
  Workout,
} from '../services/api';

export interface FitnessHubData {
  summary: FitnessHubSummary | null;
  workouts: Workout[];
  dietPlans: DietPlan[];
  expenses: Expense[];
  exerciseByGroup: Record<number, Exercise[]>;
  /** Flat list of all exercises (Row 5 "All Exercises" tab). */
  allExercises: Exercise[];
}

export interface FitnessHubHook {
  data: FitnessHubData;
  loading: boolean;
  errors: string[];
  refresh: () => Promise<void>;
}

const EMPTY: FitnessHubData = {
  summary: null,
  workouts: [],
  dietPlans: [],
  expenses: [],
  exerciseByGroup: {},
  allExercises: [],
};

/**
 * Fetch every Fitness Hub payload in parallel (Phase 70): the aggregated
 * summary, recent workouts, diet plans, expenses, and the exercise index.
 * Sidebar widgets + all five rows read from the same `summary` object.
 */
export const useFitnessHubData = (): FitnessHubHook => {
  const [data, setData] = useState<FitnessHubData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    const errs: string[] = [];
    const [summary, workouts, dietPlans, expenses, allExercises, muscleGroups] = await Promise.allSettled([
      endpoints.fitnessHub.summary(),
      endpoints.fitness.workouts(),
      endpoints.fitnessHub.dietPlans(),
      endpoints.fitnessHub.expenses(),
      endpoints.fitnessHub.exercises(),
      endpoints.fitnessHub.muscleGroups(),
    ]);
    const ok = <T,>(r: PromiseSettledResult<T>): T | null => (r.status === 'fulfilled' ? r.value : null);
    if (summary.status === 'rejected') errs.push('summary');
    if (workouts.status === 'rejected') errs.push('workouts');
    if (dietPlans.status === 'rejected') errs.push('diet-plans');
    if (expenses.status === 'rejected') errs.push('expenses');
    if (allExercises.status === 'rejected') errs.push('exercises');
    if (muscleGroups.status === 'rejected') errs.push('muscle-groups');

    const ex = ok(allExercises) ?? [];
    const groups = ok(muscleGroups) ?? [];
    const exerciseByGroup: Record<number, Exercise[]> = {};
    for (const g of groups) {
      exerciseByGroup[g.id] = ex.filter((e) => e.muscle_group_id === g.id);
    }

    setData({
      summary: ok(summary),
      workouts: ok(workouts) ?? [],
      dietPlans: ok(dietPlans) ?? [],
      expenses: ok(expenses) ?? [],
      exerciseByGroup,
      allExercises: ex,
    });
    setErrors(errs);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, errors, refresh };
};
