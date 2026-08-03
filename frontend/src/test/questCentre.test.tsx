import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StatusWindowWidget } from '../components/questcentre/StatusWindowWidget';
import { PriorityWindow } from '../components/questcentre/PriorityWindow';
import { PomodoroWidget } from '../components/questcentre/PomodoroWidget';
import { WeeklyCalendar } from '../components/rpg/WeeklyCalendar';

// The calendar fetches on mount; mock the API module so it stays silent.
vi.mock('../services/api', () => ({
  endpoints: {
    schedule: {
      list: vi.fn().mockResolvedValue([]),
      create: vi.fn().mockResolvedValue({}),
      update: vi.fn().mockResolvedValue({}),
    },
    quests: { list: vi.fn().mockResolvedValue([]) },
    missions: { list: vi.fn().mockResolvedValue([]) },
    questCentre: {
      calendar: vi.fn().mockResolvedValue({ quests_by_date: [], schedule_events: [] }),
    },
  },
}));

describe('StatusWindowWidget', () => {
  it('renders the character card with level, XP and streak', () => {
    render(
      <StatusWindowWidget
        statusWindow={{
          character: {
            id: 1, name: 'Alex', class_name: 'Wizard', level: 3, xp: 1250,
            avatar_class: 'Wizard', current_streak: 3,
          },
          xp_to_next: 750,
          today_tasks: [],
        }}
      />,
    );

    expect(screen.getByText('Alex')).toBeInTheDocument();
    expect(screen.getByLabelText('Level 3')).toBeInTheDocument();
    expect(screen.getByText('1,250')).toBeInTheDocument();
    expect(screen.getByLabelText('3 day streak')).toBeInTheDocument();
    expect(screen.getByText('750 XP left to next level')).toBeInTheDocument();
  });

  it('renders today-task checklist', () => {
    render(
      <StatusWindowWidget
        statusWindow={{
          character: {
            id: 1, name: 'Alex', class_name: 'Wizard', level: 3, xp: 1250,
            avatar_class: 'Wizard', current_streak: 0,
          },
          xp_to_next: 750,
          today_tasks: [
            { id: 1, title: 'Master Algorithms', status: 'In progress', due_date: '2026-08-16', xp_reward: 200 },
          ],
        }}
      />,
    );

    expect(screen.getByText('Master Algorithms')).toBeInTheDocument();
    expect(screen.getByText('+200 XP')).toBeInTheDocument();
  });

  it('shows an empty state without a character', () => {
    render(<StatusWindowWidget statusWindow={null} />);
    expect(screen.getByText('No character yet — seed the RPG module.')).toBeInTheDocument();
  });
});

describe('PriorityWindow', () => {
  const priority = {
    High: [{ title: 'Urgent quest', time_estimate: 45, id: 1, kind: 'quest' as const }],
    Medium: [],
    Low: [{ title: 'Low task', time_estimate: null, id: 2, kind: 'task' as const }],
  };

  it('renders the three priority folders with items', () => {
    render(
      <MemoryRouter>
        <PriorityWindow priority={priority} />
      </MemoryRouter>,
    );

    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText('Urgent quest')).toBeInTheDocument();
    expect(screen.getByText('~45m')).toBeInTheDocument();
    expect(screen.getByText('Low task')).toBeInTheDocument();
  });

  it('shows empty placeholders per folder', () => {
    render(
      <MemoryRouter>
        <PriorityWindow priority={priority} />
      </MemoryRouter>,
    );
    expect(screen.getByText('Nothing medium.')).toBeInTheDocument();
  });
});

describe('PomodoroWidget', () => {
  it('renders the timer and control buttons', () => {
    render(<PomodoroWidget />);
    expect(screen.getByText('25:00')).toBeInTheDocument();
    expect(screen.getByText('Focus')).toBeInTheDocument();
    expect(screen.getByText('Short Break')).toBeInTheDocument();
    expect(screen.getByText('Long Break')).toBeInTheDocument();
    expect(screen.getByText('Stop')).toBeInTheDocument();
  });
});

describe('WeeklyCalendar', () => {
  it('toggles between week and month views', async () => {
    const { container } = render(
      <MemoryRouter>
        <WeeklyCalendar />
      </MemoryRouter>,
    );

    expect(screen.getByText('Week')).toBeInTheDocument();
    expect(screen.getByText('Month')).toBeInTheDocument();

    // Wait for the mock data fetch to finish so the grid is interactive.
    await waitFor(() =>
      expect(screen.queryByText('Loading schedule...')).toBeNull(),
    );
    expect(container.querySelector('.qc-month-grid')).toBeNull();

    fireEvent.click(screen.getByText('Month'));
    // Wait for the month grid to render (guards against a cold-start race
    // where the view switch lands before the state update flushes).
    await waitFor(() => expect(container.querySelector('.qc-month-grid')).toBeTruthy());
  });
});
