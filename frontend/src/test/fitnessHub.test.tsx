import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ToastProvider } from '../components/shared/Toast';
import { FitnessHubDashboard } from '../pages/FitnessHubDashboard';

const { mockEndpoints } = vi.hoisted(() => {
  const summary = {
    weight_goal: { initial: 80, current: 78.5, target: 75, percent: 40 },
    pr_tracker: [
      { id: 1, exercise_name: 'Bench Press', current_weight: 60, target_weight: 100, unit: 'kg', percent: 60 },
      { id: 2, exercise_name: 'Overhead Press', current_weight: 40, target_weight: 70, unit: 'kg', percent: 57.1 },
    ],
    membership: { membership_status: 'Active', next_payment_date: '2026-08-28', days_to_payment: 26 },
    diet_plans: [
      { id: 1, title: 'Diet', is_active: true, sort_order: 0, user_id: 1 },
      { id: 2, title: 'Bulking', is_active: false, sort_order: 1, user_id: 1 },
    ],
    expenses_summary: { total: 225, by_category: { Supplement: 75, Equipment: 150, Gym: 0 } },
    weekly_split: {
      1: [
        { day: 'Mon', day_of_week: 0, split_name: 'PUSH', exercises: ['Bench Press', 'Overhead Press'] },
        { day: 'Tue', day_of_week: 1, split_name: 'PULL', exercises: ['Deadlift'] },
      ],
      2: [
        { day: 'Mon', day_of_week: 0, split_name: 'PUSH', exercises: ['Bench Press'] },
      ],
    },
    muscle_groups: [
      { id: 3, name: 'Chest', body_part: 'Upper', image_3d_url: null, sort_order: 2, user_id: 1, exercise_count: 3 },
      { id: 10, name: 'Quads', body_part: 'Lower', image_3d_url: null, sort_order: 9, user_id: 1, exercise_count: 2 },
    ],
    spec_habits: [
      {
        id: 1, name: 'Workout', goal: 'Complete a workout session every day',
        days_completed: 12, percent: 24.5,
        heatmap_7x7: Array.from({ length: 49 }, (_, i) => {
          const d = new Date(2026, 6, 1);
          d.setDate(d.getDate() + i);
          return {
            date: d.toISOString().slice(0, 10),
            completed: i % 3 !== 0,
            count: i % 3 !== 0 ? 1 : 0,
          };
        }),
      },
    ],
  };

  const mockEndpoints = {
    fitnessHub: {
      summary: vi.fn().mockResolvedValue(summary),
      exercises: vi.fn().mockResolvedValue([
        { id: 1, name: 'Bench Press', muscle_group_id: 3, sets: 4, reps: 8, weight: 60, user_id: 1 },
      ]),
      muscleGroups: vi.fn().mockResolvedValue([
        { id: 3, name: 'Chest', body_part: 'Upper', image_3d_url: null, sort_order: 2, user_id: 1 },
        { id: 10, name: 'Quads', body_part: 'Lower', image_3d_url: null, sort_order: 9, user_id: 1 },
      ]),
      dietPlans: vi.fn().mockResolvedValue(summary.diet_plans),
      expenses: vi.fn().mockResolvedValue([
        { id: 1, title: 'Protein & Creatine', cost: 55, date: '2026-07-30', category: 'Supplement', user_id: 1 },
      ]),
      deleteExpense: vi.fn().mockResolvedValue({ ok: true }),
      muscleGroupExercises: vi.fn().mockResolvedValue([]),
    },
    fitness: { workouts: vi.fn().mockResolvedValue([]) },
    habits: {
      setGoal: vi.fn().mockResolvedValue({}),
      logToday: vi.fn().mockResolvedValue({}),
    },
  };

  return { mockEndpoints, summary };
});

vi.mock('../services/api', () => ({
  endpoints: mockEndpoints,
}));

const renderPage = () =>
  render(
    <ToastProvider>
      <MemoryRouter>
        <FitnessHubDashboard />
      </MemoryRouter>
    </ToastProvider>,
  );

describe('FitnessHubDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the header, sidebar widgets and 5 rows', async () => {
    renderPage();

    // Header
    expect(await screen.findByRole('heading', { name: 'Fitness-Hub' })).toBeDefined();

    // Sidebar widgets
    expect(await screen.findByText('Quick-Action')).toBeDefined();
    expect(screen.getByText('Navigation')).toBeDefined();
    expect(screen.getAllByText('Weight Goal').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('PR-Tracker').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Membership').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Diet-Plan')).toBeDefined();

    // 5 rows
    await waitFor(() => {
      expect(screen.getByText(/Weekly-Split/)).toBeDefined();
      expect(screen.getByText(/Habit-Tracking/)).toBeDefined();
      expect(screen.getByText(/Muscle-Group/)).toBeDefined();
      expect(screen.getByText(/Expenses/)).toBeDefined();
      expect(screen.getAllByText(/Exercises/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows the weight goal progress and PR bars from the summary', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('40% to goal')).toBeDefined();
      expect(screen.getAllByText('Bench Press').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Overhead Press').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('60/100 kg')).toBeDefined();
    });
  });

  it('highlights the active diet plan', async () => {
    renderPage();

    const dietCard = await screen.findByText('Diet-Plan').then((el) => el.closest('.fh-card'));
    expect(dietCard).toBeDefined();
    const diet = within(dietCard as HTMLElement);
    expect(diet.getByText('Diet')).toBeDefined();
    expect(diet.getByText('Bulking')).toBeDefined();
    const active = diet.getByText('Diet').closest('.fh-diet-item');
    expect(active?.className).toContain('active');
  });

  it('renders the weekly split day cards with PUSH/PULL badges', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Mon').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Tue').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('PUSH').length).toBeGreaterThanOrEqual(1);
    });
    // Switch to Week 2
    const week2 = screen.getByRole('tab', { name: 'Week 2' });
    week2.click();
    expect(await screen.findByRole('button', { name: /Log Today's Workout/ })).toBeDefined();
  });

  it('renders the muscle group grid with exercise counts', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Chest').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Quads').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Total Exercises: 3')).toBeDefined();
    });
  });

  it('renders the spec habit heatmap card with goal', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText('Workout').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Complete a workout session every day')).toBeDefined();
      expect(screen.getByText((_, el) => el?.textContent === '12 days completed')).toBeDefined();
    });
    expect(screen.getByRole('button', { name: '✓ Mark as completed' })).toBeDefined();
  });
});
