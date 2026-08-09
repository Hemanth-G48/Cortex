import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Settings } from '../pages/Settings';

const { user } = vi.hoisted(() => {
  const user = {
    id: 1,
    name: 'Alex',
    avatar: null,
    avatar_class: null,
    current_level: 3,
    current_streak: 5,
    total_xp: 1200,
    created_at: '2026-01-01',
    current_weight: null,
    initial_weight: null,
    target_weight: null,
    membership_status: null,
    next_payment_date: null,
  };
  return { user };
});

vi.mock('../hooks/useAuth', () => ({
  useAuth: vi.fn(() => ({
    user,
    token: 'tok',
    role: 'student',
    loading: false,
    isAuthenticated: true,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    refreshMe: vi.fn(),
  })),
}));

vi.mock('../services/api', () => {
  return {
    endpoints: {
      kb: {
        preferences: {
          get: vi.fn().mockResolvedValue({ depth: 'overview', style: 'concise' }),
          update: vi.fn().mockResolvedValue({ depth: 'overview', style: 'concise' }),
        },
      },
      ai: {
        health: vi.fn().mockResolvedValue({ available: true, mode: 'openai', model: 'oc/deepseek-v4-flash-free', models: [], providers_count: 0 }),
        models: vi.fn().mockResolvedValue({ models: ['oc/deepseek-v4-flash-free', 'oc/gpt-4o-free'], enabled: true }),
        providers: {
          list: vi.fn().mockResolvedValue({ providers: [], active_id: null }),
          create: vi.fn(),
          update: vi.fn(),
          remove: vi.fn(),
          test: vi.fn(),
          refreshModels: vi.fn(),
          setDefault: vi.fn(),
        },
      },
      google: {
        connect: vi.fn().mockResolvedValue({ url: 'https://accounts.google.com/o/oauth2/auth?...', error: null }),
        status: vi.fn().mockResolvedValue({ connected: false, email: null, scopes: [] }),
        disconnect: vi.fn().mockResolvedValue({ connected: false }),
      },
      classroom: {
        courses: vi.fn().mockResolvedValue([]),
        assignments: vi.fn().mockResolvedValue([]),
      },
      gmail: {
        unread: vi.fn().mockResolvedValue({ count: 0 }),
        messages: vi.fn().mockResolvedValue([]),
      },
      calendarSync: {
        events: vi.fn().mockResolvedValue([]),
      },
      courses: { list: vi.fn().mockResolvedValue([]) },
      assignments: { list: vi.fn().mockResolvedValue([]) },
      exams: { list: vi.fn().mockResolvedValue([]) },
      notes: { list: vi.fn().mockResolvedValue([]) },
      tasks: { list: vi.fn().mockResolvedValue([]) },
      habits: { list: vi.fn().mockResolvedValue([]) },
      goals: { list: vi.fn().mockResolvedValue([]) },
      grades: { list: vi.fn().mockResolvedValue([]), gpa: vi.fn().mockResolvedValue({ gpa: null, courses: [] }) },
      flashcards: { list: vi.fn().mockResolvedValue([]) },
      studyPlans: { list: vi.fn().mockResolvedValue([]) },
      quests: { list: vi.fn().mockResolvedValue([]) },
      projects: { list: vi.fn().mockResolvedValue([]) },
      lifeAreas: { list: vi.fn().mockResolvedValue([]) },
      journal: { list: vi.fn().mockResolvedValue([]) },
      pomodoro: { list: vi.fn().mockResolvedValue([]) },
      schedule: { list: vi.fn().mockResolvedValue([]) },
    },
  };
});

describe('Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the profile and AI status', async () => {
    render(<Settings />);
    await waitFor(() => expect(screen.getAllByText('Alex').length).toBeGreaterThan(0));
    expect(screen.getByText(/AI enabled/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument();
  });

  it('lists the Google sync card with connect action when not connected', async () => {
    render(<Settings />);
    await waitFor(() => expect(screen.getByText('Google Sync')).toBeInTheDocument());
    expect(screen.getByText('Not connected')).toBeInTheDocument();
    expect(screen.getByText(/Connect Google/)).toBeInTheDocument();
  });

  it('offers a searchable model dropdown from the backend', async () => {
    render(<Settings />);
    await waitFor(() => expect(screen.getByLabelText(/Model override/)).toBeInTheDocument());
    const input = screen.getByLabelText(/Model override/) as HTMLInputElement;

    // Focusing the field opens the dropdown with every model listed.
    fireEvent.focus(input);
    await waitFor(() => expect(screen.getByText(/^oc\/deepseek-v4-flash-free$/)).toBeInTheDocument());
    expect(screen.getByText(/^oc\/gpt-4o-free$/)).toBeInTheDocument();

    // Typing filters the list.
    fireEvent.change(input, { target: { value: 'gpt' } });
    expect(screen.queryByText(/^oc\/deepseek-v4-flash-free$/)).not.toBeInTheDocument();
    expect(screen.getByText(/^oc\/gpt-4o-free$/)).toBeInTheDocument();

    // Selecting an option persists the override locally.
    fireEvent.mouseDown(screen.getByText(/^oc\/gpt-4o-free$/));
    expect(localStorage.getItem('slos-ai-model')).toBe('oc/gpt-4o-free');
  });
});
