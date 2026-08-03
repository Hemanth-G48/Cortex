import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ToastProvider } from '../components/shared/Toast';
import { GamifiedHabitTracker } from '../pages/GamifiedHabitTracker';

// Mock the API module so the page renders deterministically.
vi.mock('../services/api', () => {
  const habit = (id: number, name: string, habit_type: 'good' | 'bad', reward: number, penalty: number) => ({
    id, name, description: null, frequency: 'daily', target_count: 1,
    current_streak: 3, longest_streak: 5, user_id: 1, color_theme: 'blue',
    is_archived: false, habit_type, xp_reward: reward, xp_penalty: penalty,
    image_url: null, days_caught: 2,
  });
  return {
    endpoints: {
      habitTracker: {
        statusWindow: vi.fn().mockResolvedValue({
          character: { id: 1, name: 'Alex', class_name: 'Wizard', level: 3, xp: 1250, avatar_class: 'Wizard', current_streak: 3 },
          xp_to_next: 750,
          today_habits: [{ id: 1, habit_id: 1, habit_name: 'Deep Work', habit_type: 'good', status: 'Completed', xp_change: 30 }],
        }),
        summary: vi.fn().mockResolvedValue({
          total_xp: 1250, level: 3, current_streak: 3, good_today: 1, bad_today: 0,
          xp_to_next: 750, good_count: 5, bad_count: 5,
          life_areas: [
            { id: 1, name: 'Health', goal: null, image_url: null, status: 'In progress', progress_percent: 70, sort_order: 0, total_xp_earned: 58 },
          ],
          rewards_available: [{ id: 1, user_id: 1, title: 'Go for a walk', description: null, xp_cost: 30, category: 'Lifestyle', image_url: null, is_available: true, claimed_date: null, created_at: null }],
        }),
      },
      questCentre: {
        progress: vi.fn().mockResolvedValue({ year: 50, month: 40, week: 60, day: 25 }),
      },
      habits: {
        good: vi.fn().mockResolvedValue([habit(1, 'Deep Work', 'good', 30, 20)]),
        bad: vi.fn().mockResolvedValue([habit(11, 'Smoking', 'bad', 30, 20)]),
        today: vi.fn().mockResolvedValue([]),
        calendar: vi.fn().mockResolvedValue([]),
        reorder: vi.fn().mockResolvedValue({ ok: true, reordered: 1 }),
        logHabit: vi.fn().mockResolvedValue({ id: 99, habit_id: 1, date: '2026-08-02', completed: true, count: 1, type: 'good', status: 'Completed', xp_change: 30, sort_order: 0 }),
      },
      rewards: {
        claim: vi.fn().mockResolvedValue({}),
      },
      pomodoro: {
        create: vi.fn().mockResolvedValue({}),
      },
    },
  };
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <ToastProvider>
        <GamifiedHabitTracker />
      </ToastProvider>
    </MemoryRouter>,
  );

describe('GamifiedHabitTracker page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the cinematic header with the app title', () => {
    renderPage();
    expect(screen.getByText('Gamified Habit Tracker')).toBeInTheDocument();
  });

  it('renders the sidebar widgets', async () => {
    renderPage();
    expect(await screen.findByText('Status Window')).toBeInTheDocument();
    expect(await screen.findByText('Total XP')).toBeInTheDocument();
    expect(screen.getByText('Keep going! 💪')).toBeInTheDocument();
    expect(screen.getByText('Pomodoro Timer')).toBeInTheDocument();
    expect(screen.getByText('Rewards')).toBeInTheDocument();
    expect(screen.getByText('Claim Reward')).toBeInTheDocument();
  });

  it('renders Row 1: quick actions, progress bars and life areas', async () => {
    renderPage();
    expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    expect(screen.getByText('New Good Habit')).toBeInTheDocument();
    expect(screen.getByText('New Bad Habit')).toBeInTheDocument();
    expect(screen.getByText('Database')).toBeInTheDocument();
    expect(await screen.findByText('Progress')).toBeInTheDocument();
    expect(screen.getByText('Life Areas')).toBeInTheDocument();
    expect(await screen.findByText('All Time XP: 58')).toBeInTheDocument();
  });

  it('renders the Daily Good Habits and Daily Bad Habits rows', async () => {
    renderPage();
    expect(await screen.findByText('Daily Good Habits')).toBeInTheDocument();
    expect(screen.getAllByText('Deep Work').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Complete to earn: 30 XP')).toBeInTheDocument();
    expect(screen.getByText('Daily Bad Habits')).toBeInTheDocument();
    expect(screen.getByText('Smoking')).toBeInTheDocument();
    expect(screen.getByText('Shit I did it: -20 XP')).toBeInTheDocument();
  });

  it('renders both completed-habit calendar rows', async () => {
    renderPage();
    expect(await screen.findByText('Completed Good Habits')).toBeInTheDocument();
    expect(screen.getByText('Completed Bad Habits')).toBeInTheDocument();
    // Two calendar rows → two Week / Month toggles each.
    expect(screen.getAllByText('Week').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Month').length).toBeGreaterThanOrEqual(2);
  });
});
