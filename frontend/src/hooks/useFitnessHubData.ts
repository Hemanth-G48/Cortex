import { useCallback, useEffect, useState } from 'react';
import { endpoints } from '../services/api';
import type {
  DietPlan,
  Exercise,
  Expense,
  FitnessHubSummary,
  QuestCentreBoard,
  Workout,
} from '../services/api';

/** One vault hit surfaced beside a fitness widget (audit defects #85, #86). */
export interface VaultNote {
  document_id: number;
  title: string;
  snippet: string;
  /** Which fitness surface this note was searched for. */
  kind: 'weight' | 'diet' | 'pr';
}

export interface FitnessHubData {
  summary: FitnessHubSummary | null;
  /** Quest Centre board — shared XP wallet (defect #87). */
  board: QuestCentreBoard | null;
  /** Vault notes matched to the weight / diet / PR widgets (defects #85, #86). */
  vaultNotes: VaultNote[];
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
  board: null,
  vaultNotes: [],
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
const KEYWORD_QUERIES: { kind: VaultNote['kind']; query: string }[] = [
  { kind: 'weight', query: 'weight goal' },
  { kind: 'diet', query: 'diet nutrition meal plan' },
  { kind: 'pr', query: 'personal record PR max lift' },
];

/**
 * Search the vault for the phrases each fitness widget cares about, so the
 * weight-goal / diet-plan / PR cards can merge relevant notes (defects #85, #86).
 * Fails soft: a failed search simply contributes no notes.
 */
const collectVaultNotes = async (): Promise<VaultNote[]> => {
  const results = await Promise.allSettled(
    KEYWORD_QUERIES.map((k) => endpoints.kb.search.run(k.query, { mode: 'hybrid', page_size: 5 })),
  );
  const notes: VaultNote[] = [];
  const seen = new Set<number>();
  results.forEach((r, i) => {
    if (r.status !== 'fulfilled') return;
    const kind = KEYWORD_QUERIES[i].kind;
    for (const item of r.value.items ?? []) {
      if (seen.has(item.document_id)) continue;
      seen.add(item.document_id);
      notes.push({
        document_id: item.document_id,
        title: item.title,
        snippet: item.snippet,
        kind,
      });
    }
  });
  return notes;
};

export const useFitnessHubData = (): FitnessHubHook => {
  const [data, setData] = useState<FitnessHubData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    const errs: string[] = [];
    const [summary, workouts, dietPlans, expenses, allExercises, muscleGroups, board] = await Promise.allSettled([
      endpoints.fitnessHub.summary(),
      endpoints.fitness.workouts(),
      endpoints.fitnessHub.dietPlans(),
      endpoints.fitnessHub.expenses(),
      endpoints.fitnessHub.exercises(),
      endpoints.fitnessHub.muscleGroups(),
      endpoints.questCentre.board(),
    ]);
    const vaultNotes = await collectVaultNotes().catch(() => []);
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
      board: ok(board),
      vaultNotes,
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
